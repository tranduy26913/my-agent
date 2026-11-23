"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { Me } from "@/lib/me";

const MeContext = createContext<Me | null>(null);

/** Server layout lấy `getMe()` rồi đưa xuống đây, để component client đọc được mà không gọi lại. */
export function MeProvider({ me, children }: { me: Me; children: ReactNode }) {
  return <MeContext.Provider value={me}>{children}</MeContext.Provider>;
}

export function useMe(): Me {
  const me = useContext(MeContext);
  if (!me) throw new Error("useMe phải nằm trong <MeProvider>");
  return me;
}
