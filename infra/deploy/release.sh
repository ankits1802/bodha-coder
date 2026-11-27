set -euo pipefail

register() {
  local name="$1" image="$2"
  aws ecs describe-task-definition --task-definition "${TASK_FAMILY_PREFIX}${name}" --query taskDefinition --output json \
    | jq --arg image "$image" '.containerDefinitions[0].image = $image
        | {family, taskRoleArn, executionRoleArn, networkMode, containerDefinitions, requiresCompatibilities, cpu, memory, runtimePlatform}' \
    > "${RUNNER_TEMP:-/tmp}/${name}.json"
  aws ecs register-task-definition --cli-input-json "file://${RUNNER_TEMP:-/tmp}/${name}.json" \
    --query taskDefinition.taskDefinitionArn --output text
}

api_image="${ECR_API_REPOSITORY}:${TAG}"
web_image="${ECR_WEB_REPOSITORY}:${TAG}"

declare -A revisions
for name in api worker migrate bootstrap; do
  revisions[$name]="$(register "$name" "$api_image")"
done
revisions[web]="$(register web "$web_image")"

network="awsvpcConfiguration={subnets=[${TASK_SUBNETS}],securityGroups=[${TASK_SECURITY_GROUP}],assignPublicIp=ENABLED}"
migration="$(aws ecs run-task --cluster "$ECS_CLUSTER" --task-definition "${revisions[migrate]}" --launch-type FARGATE \
  --network-configuration "$network" --query 'tasks[0].taskArn' --output text)"
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$migration"
exit_code="$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$migration" \
  --query 'tasks[0].containers[0].exitCode' --output text)"
if [ "$exit_code" != "0" ]; then
  echo "Migrations failed with exit code ${exit_code}; services were not changed."
  exit 1
fi

for name in api worker web; do
  aws ecs update-service --cluster "$ECS_CLUSTER" --service "$name" --task-definition "${revisions[$name]}" \
    --query service.serviceName --output text
done
aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services api worker web
echo "Released ${TAG}."
