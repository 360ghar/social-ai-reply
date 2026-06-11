"use client";

import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface FilterOption {
  label: string;
  value: string;
}

/**
 * Generic select-filter configuration so new filters (e.g. `buying_stage`)
 * can be added later without changing this component.
 */
export interface FilterConfig {
  id: string;
  /** Placeholder shown when no value is selected (e.g. "All Campaigns"). */
  placeholder: string;
  options: FilterOption[];
  value: string;
  onChange: (value: string) => void;
}

interface FiltersBarProps {
  search?: {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
  };
  filters?: FilterConfig[];
  className?: string;
}

/** Search box + configurable select filters for the opportunity queue. */
export function FiltersBar({ search, filters = [], className }: FiltersBarProps) {
  if (!search && filters.length === 0) {
    return null;
  }

  return (
    <div className={cn("flex flex-col sm:flex-row sm:items-center gap-2", className)}>
      {search && (
        <div className="relative flex-1 min-w-0">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            value={search.value}
            onChange={(event) => search.onChange(event.target.value)}
            placeholder={search.placeholder ?? "Search conversations"}
            className="h-8 pl-8 text-xs"
          />
        </div>
      )}
      {filters.map((filter) => (
        <Select key={filter.id} value={filter.value} onValueChange={(v) => filter.onChange(v ?? "")}>
          <SelectTrigger className="h-8 w-[160px] text-xs">
            <SelectValue placeholder={filter.placeholder} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">{filter.placeholder}</SelectItem>
            {filter.options.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}
    </div>
  );
}
