"use client";

import { motion } from "framer-motion";
import { BookOpen, ExternalLink, ShieldCheck } from "lucide-react";
import { useT } from "@/lib/i18n";
import type { Citation } from "@/lib/types";

/**
 * Sources behind a plan.
 *
 * The `origin` split is the point: "rules" citations are the verified official
 * procedure the plan is built from, while "uploaded_document" citations are
 * supporting passages retrieved from the knowledge base. Showing them
 * identically would blur the line between verified fact and AI-assembled
 * suggestion, which is the whole trust model here.
 */
export default function CitationList({ citations }: { citations: Citation[] }) {
  const t = useT();
  if (!citations?.length) return null;

  const official  = citations.filter((c) => c.origin === "rules");
  const supporting = citations.filter((c) => c.origin !== "rules");

  return (
    <div className="space-y-4">
      {official.length > 0 && (
        <Section
          Icon={ShieldCheck}
          iconClass="text-(--success)"
          title={t("citations.officialTitle")}
          caption={t("citations.officialCaption")}
          citations={official}
        />
      )}
      {supporting.length > 0 && (
        <Section
          Icon={BookOpen}
          iconClass="text-(--primary)"
          title={t("citations.supportingTitle")}
          caption={t("citations.supportingCaption")}
          citations={supporting}
        />
      )}
    </div>
  );
}

function Section({
  Icon, iconClass, title, caption, citations,
}: {
  Icon: typeof BookOpen;
  iconClass: string;
  title: string;
  caption: string;
  citations: Citation[];
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <Icon size={16} className={iconClass} />
        <p className="text-sm font-bold text-(--foreground)">{title}</p>
      </div>
      <p className="mb-2 text-xs text-(--muted-fg)">{caption}</p>

      <ul className="space-y-2">
        {citations.map((c, i) => (
          <motion.li
            key={`${c.source_url ?? c.title}-${i}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-xl border border-(--border) bg-white p-3"
          >
            {c.source_url ? (
              <a
                href={c.source_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-start gap-1.5 text-sm font-semibold text-(--primary) hover:underline"
              >
                <span className="min-w-0 flex-1">{c.title}</span>
                <ExternalLink size={13} className="mt-0.5 shrink-0" />
              </a>
            ) : (
              // An admin can upload a circular with no public URL. It is still
              // a real source, so name it rather than hiding it.
              <p className="text-sm font-semibold text-(--foreground)">{c.title}</p>
            )}
            {c.snippet && (
              <p className="mt-1.5 text-xs leading-relaxed text-(--muted-fg)">
                &ldquo;{c.snippet.trim()}&rdquo;
              </p>
            )}
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
