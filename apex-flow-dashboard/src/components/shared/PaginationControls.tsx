"use client";

import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
  pageSize?: number;
  totalItems?: number;
  loading?: boolean;
}

export function PaginationControls({
  currentPage,
  totalPages,
  onPageChange,
  pageSize = 50,
  totalItems,
  loading = false,
}: PaginationControlsProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-2 py-3">
      {totalItems !== undefined ? (
        <p className="text-xs text-zinc-400 font-mono">
          Showing <span className="text-zinc-200 font-bold">{(currentPage - 1) * pageSize + 1}</span> to{" "}
          <span className="text-zinc-200 font-bold">{Math.min(currentPage * pageSize, totalItems)}</span> of{" "}
          <span className="text-zinc-200 font-bold">{totalItems}</span> entries
        </p>
      ) : (
        <div />
      )}

      <div className="flex items-center gap-2">
        <Button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1 || loading}
          variant="outline"
          size="sm"
          className="h-8 text-xs border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] gap-1 disabled:opacity-40"
        >
          <ChevronLeft size={14} />
          <span>Previous</span>
        </Button>

        <div className="px-3 py-1 rounded-md bg-[#161620] border border-white/10 text-xs font-mono text-zinc-300">
          Page <span className="text-violet-400 font-bold">{currentPage}</span> of{" "}
          <span className="text-zinc-100 font-bold">{totalPages}</span>
        </div>

        <Button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages || loading}
          variant="outline"
          size="sm"
          className="h-8 text-xs border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] gap-1 disabled:opacity-40"
        >
          <span>Next</span>
          <ChevronRight size={14} />
        </Button>
      </div>
    </div>
  );
}
