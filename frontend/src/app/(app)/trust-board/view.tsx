"use client";


import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import NextPromotion from "@/components/trust-board/NextPromotion";
import SellerCard from "@/components/trust-board/SellerCard";
import TrustLadder from "@/components/trust-board/TrustLadder";
import { getSellers } from "@/lib/api";
import type { Seller } from "@/lib/types";

export default function TrustBoardPage() {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSellers()
      .then((res) => {
        if (!cancelled) setSellers(res.items);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Something went wrong.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <PageHeader
        title="Trust Board"
        subtitle="Sellers earn higher spending limits by completing verified work."
      />

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-lg bg-block/10 p-3 text-sm text-[#b3303c] dark:text-block"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-56 animate-pulse rounded-2xl bg-foreground/5"
            />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {sellers.map((s) => (
            <SellerCard key={s.id} seller={s} />
          ))}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <TrustLadder />
        </div>
        <div className="lg:col-span-2">
          <NextPromotion sellers={sellers} />
        </div>
      </div>
    </>
  );
}