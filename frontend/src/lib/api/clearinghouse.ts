import { request } from "./client";
import type { ChargeList, ClearinghouseView, ConnectionCheck, ConnectionInput, HostKey } from "./types";

const CLEARINGHOUSE = "/api/practice/clearinghouse";
const CHARGES = "/api/practice/charges";

export function getClearinghouse(): Promise<ClearinghouseView> {
  return request<ClearinghouseView>(CLEARINGHOUSE);
}

export function saveClearinghouse(connection: ConnectionInput): Promise<ClearinghouseView> {
  return request<ClearinghouseView>(CLEARINGHOUSE, { method: "PUT", body: connection });
}

export function removeClearinghouse(): Promise<ClearinghouseView> {
  return request<ClearinghouseView>(CLEARINGHOUSE, { method: "DELETE" });
}

export function readHostKey(host: string, port: number): Promise<HostKey> {
  return request<HostKey>(`${CLEARINGHOUSE}/host-key`, { method: "POST", body: { host, port } });
}

export function testClearinghouse(): Promise<ConnectionCheck> {
  return request<ConnectionCheck>(`${CLEARINGHOUSE}/test`, { method: "POST" });
}

export function getCharges(): Promise<ChargeList> {
  return request<ChargeList>(CHARGES);
}

export function setCharge(code: string, cents: number): Promise<ChargeList> {
  return request<ChargeList>(`${CHARGES}/${encodeURIComponent(code)}`, { method: "PUT", body: { cents } });
}

export function removeCharge(code: string): Promise<ChargeList> {
  return request<ChargeList>(`${CHARGES}/${encodeURIComponent(code)}`, { method: "DELETE" });
}

export function importCharges(csv: string): Promise<ChargeList> {
  return request<ChargeList>(`${CHARGES}/import`, { method: "POST", body: { csv } });
}
