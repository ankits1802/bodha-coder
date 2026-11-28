import type { AuthKind, ClaimTransport, ClaimUsage, ClearinghouseConnection, ConnectionInput, IdQualifier } from "@/lib/api/types";
import { CLEARINGHOUSE_TEXT } from "./strings";

export const ID_QUALIFIERS: readonly IdQualifier[] = ["ZZ", "01", "14", "20", "27", "28", "29", "30", "33"];
export const DEFAULT_PORT = "22";

const INTERCHANGE_ID = /^[A-Za-z0-9-]{1,15}$/;
const HIGHEST_PORT = 65535;

export interface ConnectionDraft {
  name: string;
  usage: ClaimUsage;
  transport: ClaimTransport;
  sender_qualifier: IdQualifier;
  sender_id: string;
  receiver_qualifier: IdQualifier;
  receiver_id: string;
  receiver_name: string;
  host: string;
  port: string;
  username: string;
  auth_kind: AuthKind;
  secret: string;
  host_key_sha256: string;
  outbound_folder: string;
  inbound_folder: string;
}

export type ConnectionErrors = Partial<Record<keyof ConnectionDraft, string>>;
export type DraftChange = (change: Partial<ConnectionDraft>) => void;

export function connectionDraftFrom(connection: ClearinghouseConnection | null): ConnectionDraft {
  return {
    name: connection?.name ?? "",
    usage: connection?.usage ?? "test",
    transport: connection?.transport ?? "sftp",
    sender_qualifier: connection?.sender_qualifier ?? "ZZ",
    sender_id: connection?.sender_id ?? "",
    receiver_qualifier: connection?.receiver_qualifier ?? "ZZ",
    receiver_id: connection?.receiver_id ?? "",
    receiver_name: connection?.receiver_name ?? "",
    host: connection?.host ?? "",
    port: connection?.port ? String(connection.port) : DEFAULT_PORT,
    username: connection?.username ?? "",
    auth_kind: connection?.auth_kind ?? "password",
    secret: "",
    host_key_sha256: connection?.host_key_sha256 ?? "",
    outbound_folder: connection?.outbound_folder ?? "",
    inbound_folder: connection?.inbound_folder ?? "",
  };
}

export function keepsSavedSecret(draft: ConnectionDraft, connection: ClearinghouseConnection | null): boolean {
  if (!connection?.secret_saved || connection.transport !== "sftp") return false;
  const sameLogin = connection.host === draft.host.trim().toLowerCase() && connection.username === draft.username.trim();
  return sameLogin && String(connection.port) === draft.port.trim() && connection.auth_kind === draft.auth_kind;
}

export function validateConnection(draft: ConnectionDraft, connection: ClearinghouseConnection | null): ConnectionErrors {
  const words = CLEARINGHOUSE_TEXT.errors;
  const errors: ConnectionErrors = {};
  if (!draft.name.trim()) errors.name = words.name;
  if (!INTERCHANGE_ID.test(draft.sender_id.trim())) errors.sender_id = words.senderId;
  if (!INTERCHANGE_ID.test(draft.receiver_id.trim())) errors.receiver_id = words.receiverId;
  if (!draft.receiver_name.trim()) errors.receiver_name = words.receiverName;
  return draft.transport === "sftp" ? { ...errors, ...sftpErrors(draft, connection) } : errors;
}

function sftpErrors(draft: ConnectionDraft, connection: ClearinghouseConnection | null): ConnectionErrors {
  const words = CLEARINGHOUSE_TEXT.errors;
  const errors: ConnectionErrors = {};
  const port = Number(draft.port);
  if (!draft.host.trim()) errors.host = words.host;
  if (!Number.isInteger(port) || port < 1 || port > HIGHEST_PORT) errors.port = words.port;
  if (!draft.username.trim()) errors.username = words.username;
  if (!draft.secret.trim() && !keepsSavedSecret(draft, connection)) errors.secret = words.secret;
  if (!draft.outbound_folder.trim()) errors.outbound_folder = words.folder;
  if (!draft.inbound_folder.trim()) errors.inbound_folder = words.folder;
  if (!draft.host_key_sha256) errors.host_key_sha256 = words.hostKey;
  return errors;
}

export function connectionInputFrom(draft: ConnectionDraft): ConnectionInput {
  const identity: ConnectionInput = {
    name: draft.name.trim(),
    usage: draft.usage,
    transport: draft.transport,
    sender_qualifier: draft.sender_qualifier,
    sender_id: draft.sender_id.trim().toUpperCase(),
    receiver_qualifier: draft.receiver_qualifier,
    receiver_id: draft.receiver_id.trim().toUpperCase(),
    receiver_name: draft.receiver_name.trim(),
  };
  if (draft.transport !== "sftp") return identity;
  const secret = draft.secret.trim() ? draft.secret : null;
  return {
    ...identity,
    host: draft.host.trim(),
    port: Number(draft.port),
    username: draft.username.trim(),
    auth_kind: draft.auth_kind,
    password: draft.auth_kind === "password" ? secret : null,
    private_key: draft.auth_kind === "key" ? secret : null,
    host_key_sha256: draft.host_key_sha256,
    outbound_folder: draft.outbound_folder.trim(),
    inbound_folder: draft.inbound_folder.trim(),
  };
}
