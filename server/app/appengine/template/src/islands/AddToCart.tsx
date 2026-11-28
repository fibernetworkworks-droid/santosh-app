"use client"; // v0.999.82 D8 wave 6: Add to cart on a catalogue item her shop sells - an island
// Hoola App Engine - Hoola's own kit file. It hands the item to the cart island of the page (the same shop, prices and
// stock as her website: the shop prices the order, never this button).
import * as React from "react";
import { ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AddToCart({ slug, name }: { slug: string; name: string }) {
  const add = () => {
    const detail = { slug, name, price: null };
    const w = window as unknown as { __hoolaCartReady?: boolean; __hoolaCart?: unknown[] };
    if (w.__hoolaCartReady) window.dispatchEvent(new CustomEvent("hoola-cart", { detail }));
    else (w.__hoolaCart = w.__hoolaCart || []).push(detail);    // the cart is still waking: it takes this first
  };
  return (
    <Button size="lg" onClick={add} className="w-fit">
      <ShoppingBag className="size-4" aria-hidden="true" />
      Add to cart
    </Button>
  );
}
