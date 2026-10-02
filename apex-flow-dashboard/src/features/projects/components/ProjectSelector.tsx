"use client";

import React, { useState } from "react";
import { FolderGit2, ChevronDown, Plus, Check, Loader2 } from "lucide-react";
import { useProject } from "../context";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ProjectSelector() {
  const { projects, currentProject, selectProject, createNewProject, loading } = useProject();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      setCreating(true);
      setError(null);
      await createNewProject(newProjectName.trim());
      setNewProjectName("");
      setModalOpen(false);
      setDropdownOpen(false);
    } catch (err: any) {
      setError(err?.message || "Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  if (loading && !currentProject) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-400 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10">
        <Loader2 size={13} className="animate-spin text-violet-400" />
        <span>Loading project...</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        id="project-selector-btn"
        onClick={() => setDropdownOpen((o) => !o)}
        className="flex items-center gap-2 bg-[#1b1b26] hover:bg-[#232332] text-zinc-200 border border-white/10 px-3 py-1.5 rounded-lg transition-all text-xs font-medium focus:outline-none focus:ring-1 focus:ring-violet-500"
      >
        <FolderGit2 size={14} className="text-violet-400 shrink-0" />
        <span className="truncate max-w-[140px]">{currentProject?.name || "Select Project"}</span>
        <ChevronDown size={12} className="text-zinc-400 shrink-0" />
      </button>

      {dropdownOpen && (
        <div className="absolute right-0 mt-1.5 w-64 bg-[#161620] border border-white/10 rounded-xl shadow-2xl p-1.5 z-50 animate-in fade-in slide-in-from-top-1">
          <div className="px-2.5 py-1.5 mb-1 border-b border-white/10 flex items-center justify-between">
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
              Projects ({projects.length})
            </span>
          </div>

          <div className="max-h-56 overflow-y-auto space-y-0.5">
            {projects.map((proj) => {
              const isSelected = currentProject?.id === proj.id;
              return (
                <button
                  key={proj.id}
                  onClick={() => {
                    selectProject(proj.id);
                    setDropdownOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                    isSelected
                      ? "bg-violet-600/20 text-violet-300 font-semibold border border-violet-500/30"
                      : "text-zinc-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <span className="truncate">{proj.name}</span>
                  {isSelected && <Check size={13} className="text-violet-400 shrink-0 ml-2" />}
                </button>
              );
            })}
          </div>

          <div className="mt-1 pt-1 border-t border-white/10">
            <button
              onClick={() => {
                setModalOpen(true);
                setDropdownOpen(false);
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-violet-400 hover:bg-violet-950/40 hover:text-violet-300 transition-colors font-medium"
            >
              <Plus size={13} />
              <span>Create New Project</span>
            </button>
          </div>
        </div>
      )}

      {/* Create Project Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-[#161620] border-white/10 text-zinc-100 sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-zinc-100 flex items-center gap-2">
              <FolderGit2 className="text-violet-400" size={18} />
              <span>Create New Project</span>
            </DialogTitle>
            <DialogDescription className="text-zinc-400 text-xs">
              Organize your workflow runs, step queues, and SDK workers under an isolated project.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreate} className="space-y-4 py-2">
            {error && (
              <div className="p-2.5 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="project-name" className="text-xs text-zinc-300">
                Project Name
              </Label>
              <Input
                id="project-name"
                placeholder="e.g. Data Pipeline Production"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="bg-[#111118] border-white/10 text-zinc-100 focus:border-violet-500 focus:ring-violet-500 text-xs"
                autoFocus
              />
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setModalOpen(false)}
                className="text-zinc-400 hover:text-white text-xs"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={creating || !newProjectName.trim()}
                className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold"
              >
                {creating ? <Loader2 size={13} className="animate-spin mr-1.5" /> : null}
                <span>Create Project</span>
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
