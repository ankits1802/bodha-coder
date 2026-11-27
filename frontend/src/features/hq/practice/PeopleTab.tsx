"use client";

import { MemberIdentity, MemberLastSeen, MemberTwoStep } from "@/components/shared/MemberCells";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { useRemote } from "@/hooks/useRemote";
import { getHqPracticePeople } from "@/lib/api/hq";
import type { HqPerson } from "@/lib/api/types";
import { MEMBER_STATUS_LABELS, ROLE_LABELS } from "@/lib/labels";
import { HQ_TEXT } from "../strings";
import { STATUS_TONES } from "../team/hqTeamModel";

const words = HQ_TEXT.practice.people;

function PeopleTable({ people }: { people: HqPerson[] }) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.name}</Th>
          <Th>{columns.role}</Th>
          <Th>{columns.status}</Th>
          <Th>{columns.twoStep}</Th>
          <Th>{columns.lastActive}</Th>
        </tr>
      </thead>
      <tbody>
        {people.map((person) => (
          <Tr key={person.id}>
            <Td>
              <MemberIdentity member={person} isSelf={false} />
            </Td>
            <Td>{ROLE_LABELS[person.role]}</Td>
            <Td>
              <StatusDot tone={STATUS_TONES[person.status]}>{MEMBER_STATUS_LABELS[person.status]}</StatusDot>
            </Td>
            <Td>
              <MemberTwoStep member={person} />
            </Td>
            <Td>
              <MemberLastSeen member={person} />
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

export function PeopleTab({ practiceId }: { practiceId: string }) {
  const people = useRemote(`hq-practice-people:${practiceId}`, () => getHqPracticePeople(practiceId));
  return (
    <Panel aria-label={words.tableLabel}>
      <RemoteView
        state={people.state}
        text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
        isEmpty={(data) => data.length === 0}
        onRetry={people.reload}
      >
        {(data) => <PeopleTable people={data} />}
      </RemoteView>
    </Panel>
  );
}
