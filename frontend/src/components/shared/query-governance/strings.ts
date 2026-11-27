export const QUERY_TEXT = {
  title: "Provider queries",
  tableLabel: "Provider queries by provider in this period",
  columns: {
    provider: "Provider",
    queries: "Queries",
    per100: "Per 100 notes",
    responded: "Answered",
    medianWait: "Median wait",
    agreed: "Agreed",
    repeated: "Repeated",
  },
  allProviders: "All providers",
  noQueries: "No provider queries in this period",
  loading: "Loading provider queries",
  retry: "Try again",
  exportAddendum: "Export addendum",
  defaultAddendumName: "addendum.txt",
} as const;
