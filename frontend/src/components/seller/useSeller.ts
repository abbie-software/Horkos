"use client";

import { useEffect, useState } from "react";

const KEY = "horkos-seller";

export function useSeller() {
  const [sellerId, setSellerId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      setSellerId(sessionStorage.getItem(KEY));
    } catch {}
    setReady(true);
  }, []);

  function choose(id: string | null) {
    setSellerId(id);
    try {
      if (id) sessionStorage.setItem(KEY, id);
      else sessionStorage.removeItem(KEY);
    } catch {}
  }

  return { sellerId, ready, choose };
}