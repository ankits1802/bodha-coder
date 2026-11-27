import { readFile, writeFile } from "node:fs/promises";
import openapiTS, { astToString } from "openapi-typescript";
import ts from "typescript";

const root = new URL("../", import.meta.url);
const document = JSON.parse(await readFile(new URL("openapi.json", root), "utf8"));
const generated = astToString(await openapiTS(document, { defaultNonNullable: false, silent: true }));
const parsed = ts.createSourceFile("schema.ts", generated, ts.ScriptTarget.Latest, false, ts.ScriptKind.TS);
const printer = ts.createPrinter({ newLine: ts.NewLineKind.LineFeed, removeComments: true });
await writeFile(new URL("src/lib/api/schema.ts", root), printer.printFile(parsed));
