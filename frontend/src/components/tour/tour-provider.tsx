"use client";

import { createContext, useContext, useState, useCallback, useRef } from "react";
import { driver, type Driver } from "driver.js";
import "driver.js/dist/driver.css";
import "./tour-styles.css";
import { apiFetch } from "@/lib/api/client";
import { useAuth } from "@clerk/nextjs";
import { usePathname } from "next/navigation";
import { useUserRole } from "@/hooks/use-user-role";
import { getTourStepsForPage, type TechnicalLevel } from "./tour-steps";

interface TourContextValue {
  startTour: (tourId?: string) => void;
  startCurrentPageTour: () => void;
  isTourActive: boolean;
}

const TourContext = createContext<TourContextValue>({
  startTour: () => {},
  startCurrentPageTour: () => {},
  isTourActive: false,
});

export function useTour() {
  return useContext(TourContext);
}

export function TourProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();
  const { profile } = useUserRole();
  const pathname = usePathname();
  const [isTourActive, setIsTourActive] = useState(false);
  const driverRef = useRef<Driver | null>(null);

  const startTour = useCallback(
    (tourId?: string) => {
      const level =
        (profile?.technical_level as TechnicalLevel) || "vibe_coder";
      const targetPath = tourId || pathname;
      const steps = getTourStepsForPage(targetPath, level);
      if (!steps || steps.length === 0) return;

      // Destroy any existing tour
      driverRef.current?.destroy();

      const d = driver({
        showProgress: true,
        animate: true,
        allowClose: true,
        overlayClickBehavior: "close",
        stagePadding: 8,
        stageRadius: 8,
        steps: steps.map((s) => ({
          element: s.element,
          popover: {
            title: s.popover.title,
            description: s.popover.description,
            side: s.popover.side,
          },
        })),
        onDestroyStarted: () => {
          setIsTourActive(false);
          driverRef.current?.destroy();
          // Mark tour complete when user finishes or closes
          getToken().then((token) => {
            apiFetch("/api/user/tour/complete", {
              method: "POST",
              token: token ?? undefined,
            }).catch(() => {});
          });
        },
      });

      driverRef.current = d;
      setIsTourActive(true);
      d.drive();
    },
    [pathname, profile, getToken],
  );

  const startCurrentPageTour = useCallback(() => {
    startTour(pathname);
  }, [startTour, pathname]);

  return (
    <TourContext.Provider
      value={{ startTour, startCurrentPageTour, isTourActive }}
    >
      {children}
    </TourContext.Provider>
  );
}
