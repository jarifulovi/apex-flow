"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useAuth } from "@/features/auth/hooks";
import { getProjects, getOrCreateDefaultProject, createProject as createProjectApi } from "./api";
import type { Project } from "./types";

interface ProjectContextType {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  selectProject: (projectId: string) => void;
  createNewProject: (name: string) => Promise<Project | null>;
  refreshProjects: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

const STORAGE_KEY = "apexflow_active_project_id";

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  const initProjects = useCallback(async () => {
    if (!accessToken) {
      setProjects([]);
      setCurrentProject(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      let list = await getProjects(accessToken).catch(() => []);
      
      if (list.length === 0) {
        // Auto-create default project if user has no projects
        const defaultProj = await getOrCreateDefaultProject(accessToken);
        list = [defaultProj];
      }

      setProjects(list);

      // Restore stored project preference if valid
      const storedId = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
      const found = list.find((p) => p.id === storedId);

      if (found) {
        setCurrentProject(found);
      } else {
        setCurrentProject(list[0]);
        if (typeof window !== "undefined") {
          localStorage.setItem(STORAGE_KEY, list[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to initialize projects:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    initProjects();
  }, [initProjects]);

  const selectProject = (projectId: string) => {
    const proj = projects.find((p) => p.id === projectId);
    if (proj) {
      setCurrentProject(proj);
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, proj.id);
      }
    }
  };

  const createNewProject = async (name: string): Promise<Project | null> => {
    if (!accessToken) return null;
    try {
      const newProj = await createProjectApi(accessToken, { name });
      const updatedList = [...projects, newProj];
      setProjects(updatedList);
      setCurrentProject(newProj);
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, newProj.id);
      }
      return newProj;
    } catch (err) {
      console.error("Failed to create project:", err);
      throw err;
    }
  };

  const refreshProjects = async () => {
    if (!accessToken) return;
    const list = await getProjects(accessToken);
    setProjects(list);
    if (currentProject) {
      const refreshed = list.find((p) => p.id === currentProject.id);
      if (refreshed) setCurrentProject(refreshed);
    }
  };

  return (
    <ProjectContext.Provider
      value={{
        projects,
        currentProject,
        loading,
        selectProject,
        createNewProject,
        refreshProjects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return context;
}
