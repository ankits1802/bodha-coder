import { request } from "./client";
import type { EmailIntake, IntakeMessagePage, IntakeTest } from "./types";

const EMAIL_INTAKE = "/api/practice/email-intake";

export function getEmailIntake(): Promise<EmailIntake> {
  return request<EmailIntake>(EMAIL_INTAKE);
}

export function issueIntakeAddress(): Promise<EmailIntake> {
  return request<EmailIntake>(`${EMAIL_INTAKE}/address`, { method: "POST" });
}

export function retireIntakeAddress(): Promise<EmailIntake> {
  return request<EmailIntake>(`${EMAIL_INTAKE}/address`, { method: "DELETE" });
}

export function allowIntakeSender(sender: string): Promise<EmailIntake> {
  return request<EmailIntake>(`${EMAIL_INTAKE}/senders`, { body: { sender } });
}

export function removeIntakeSender(senderId: string): Promise<EmailIntake> {
  return request<EmailIntake>(`${EMAIL_INTAKE}/senders/${encodeURIComponent(senderId)}`, { method: "DELETE" });
}

export function sendIntakeTest(): Promise<IntakeTest> {
  return request<IntakeTest>(`${EMAIL_INTAKE}/tests`, { method: "POST" });
}

export function getIntakeTest(testId: string): Promise<IntakeTest> {
  return request<IntakeTest>(`${EMAIL_INTAKE}/tests/${encodeURIComponent(testId)}`);
}

export function getIntakeMessages(offset: number): Promise<IntakeMessagePage> {
  return request<IntakeMessagePage>(`${EMAIL_INTAKE}/messages`, { query: { offset } });
}
