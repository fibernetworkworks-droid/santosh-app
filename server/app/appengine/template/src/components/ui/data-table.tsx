import * as React from "react";
import {
  columnFilteringFeature,
  createFilteredRowModel,
  createPaginatedRowModel,
  createSortedRowModel,
  filterFn_includesString,
  globalFilteringFeature,
  rowPaginationFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/** One column of a DataTable: `key` is the field of a row; `render` draws the cell yourself (a badge, a button...). */
export type DataColumn<T> = {
  key: keyof T & string;
  label: string;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  render?: (row: T) => React.ReactNode;
};

// the table's features, made once (TanStack Table v9: only what is registered is in the bundle)
const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric },
  columnFilteringFeature,
  globalFilteringFeature,
  filteredRowModel: createFilteredRowModel(),
  filterFns: { includesString: filterFn_includesString },
  rowPaginationFeature,
  paginatedRowModel: createPaginatedRowModel(),
});

/**
 * A real data table (TanStack Table v9): click a heading to sort, a search box filters every column, pages at the
 * bottom. Pass plain rows and the columns to show; nothing else to wire. Example:
 *   <DataTable rows={orders} columns={[{ key: "customer", label: "Customer" }, { key: "total", label: "Total", align: "right",
 *     render: (o) => formatMoney(o.total) }]} searchLabel="Search orders" />
 */
export function DataTable<T extends Record<string, unknown>>({
  rows,
  columns,
  pageSize = 10,
  search = true,
  searchLabel = "Search",
  empty = "Nothing here yet.",
  onRowClick,
  className,
}: {
  rows: T[];
  columns: DataColumn<T>[];
  pageSize?: number;
  search?: boolean;
  searchLabel?: string;
  empty?: React.ReactNode;
  onRowClick?: (row: T) => void;
  className?: string;
}) {
  const defs = React.useMemo(
    () =>
      columns.map((c) => ({
        id: c.key,
        accessorKey: c.key,
        header: c.label,
        enableSorting: c.sortable !== false,
        sortFn: "alphanumeric" as const,
        filterFn: "includesString" as const,
        cell: (info: { row: { original: T } }) =>
          c.render ? c.render(info.row.original) : String(info.row.original[c.key] ?? ""),
      })),
    [columns],
  );
  const [globalFilter, setGlobalFilter] = React.useState("");
  const table = useTable({
    features,
    // the column shapes above match TanStack's accessor columns; the generic types are kept out of app code on purpose
    columns: defs as never,
    data: rows,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter as never,
    globalFilterFn: "includesString",
    initialState: { pagination: { pageIndex: 0, pageSize } },
  });
  const align = (k: string) => columns.find((c) => c.key === k)?.align ?? "left";
  const pageRows = table.getRowModel().rows;
  const pages = Math.max(1, table.getPageCount());
  const page = (table.state.pagination?.pageIndex ?? 0) + 1;

  return (
    <div className={cn("space-y-3", className)}>
      {search && (
        <label className="relative block max-w-xs">
          <span className="sr-only">{searchLabel}</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <Input
            value={globalFilter}
            onChange={(e) => {
              setGlobalFilter(e.target.value);
              table.setPageIndex(0);
            }}
            placeholder={searchLabel}
            className="pl-9"
          />
        </label>
      )}
      <div className="rounded-card border border-line bg-surface">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((group) => (
              <TableRow key={group.id}>
                {group.headers.map((header) => {
                  const sorted = header.column.getIsSorted();
                  const can = header.column.getCanSort();
                  const a = align(header.column.id);
                  return (
                    <TableHead
                      key={header.id}
                      aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
                      className={cn(a === "right" && "text-right", a === "center" && "text-center")}
                    >
                      {can ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className="inline-flex items-center gap-1 rounded-control font-medium hover:text-ink focus-visible:outline-2 focus-visible:outline-primary"
                        >
                          <table.FlexRender header={header} />
                          {sorted === "asc" ? (
                            <ArrowUp className="h-3.5 w-3.5" aria-hidden />
                          ) : sorted === "desc" ? (
                            <ArrowDown className="h-3.5 w-3.5" aria-hidden />
                          ) : (
                            <ArrowUpDown className="h-3.5 w-3.5 opacity-50" aria-hidden />
                          )}
                        </button>
                      ) : (
                        <table.FlexRender header={header} />
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {pageRows.length ? (
              pageRows.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row.original as T) : undefined}
                  className={cn(onRowClick && "cursor-pointer")}
                >
                  {row.getAllCells().map((cell) => {
                    const a = align(cell.column.id);
                    return (
                      <TableCell key={cell.id} className={cn(a === "right" && "text-right tabular-nums", a === "center" && "text-center")}>
                        <table.FlexRender cell={cell} />
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="py-10 text-center text-muted">
                  {globalFilter ? `Nothing matches "${globalFilter}".` : empty}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm text-muted">
          <span>
            Page {page} of {pages}
          </span>
          <Button variant="outline" size="icon-sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()} aria-label="Previous page">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon-sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()} aria-label="Next page">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
