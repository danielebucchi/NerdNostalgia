import Link from "next/link";
import type { Article } from "@/lib/types";
import { formatPrice } from "@/lib/api";

const CONDITION_LABEL: Record<Article["condition"], string> = {
  NEW: "NUOVO",
  USED: "USATO",
  REFURBISHED: "REVISIONATO",
  FOR_PARTS: "PER PEZZI",
};

const CONDITION_COLOR: Record<Article["condition"], string> = {
  NEW: "text-retro-green",
  USED: "text-retro-neon",
  REFURBISHED: "text-retro-sun",
  FOR_PARTS: "text-retro-accent",
};

export function ArticleCard({ article }: { article: Article }) {
  const cover = article.images?.[0];

  return (
    <Link
      href={`/articles/${article.id}`}
      className="card block p-3 hover:translate-y-[-2px] transition-transform"
    >
      <div className="aspect-square w-full bg-[#0d0221] border-2 border-retro-neon relative overflow-hidden">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover}
            alt={article.title}
            className="pixel-img w-full h-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center font-pixel text-retro-neon text-xs text-center px-2">
            NO PHOTO<br />?_?
          </div>
        )}
        {article.status === "SOLD" && (
          <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
            <span className="font-pixel text-retro-accent text-xl rotate-[-8deg]">
              SOLD OUT
            </span>
          </div>
        )}
      </div>

      <div className="mt-3 relative z-10">
        <h3 className="font-pixel text-[11px] leading-tight text-retro-sun line-clamp-2 h-[28px]">
          {article.title}
        </h3>
        <div className="mt-2 flex items-center justify-between">
          <span className={`badge ${CONDITION_COLOR[article.condition]}`}>
            {CONDITION_LABEL[article.condition]}
          </span>
          {article.category && (
            <span className="font-retro text-retro-neon text-sm uppercase">
              {article.category}
            </span>
          )}
        </div>
        <div className="mt-3 font-pixel text-retro-accent glow text-sm">
          {formatPrice(article)}
        </div>
      </div>
    </Link>
  );
}
