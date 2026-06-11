"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { SheetPanel } from "@/components/shared/sheet-panel";
import type { Opportunity } from "@/lib/api";
import { redditUrl } from "@/lib/reddit";

interface OpportunityDetailPanelProps {
  opportunity: Opportunity | null;
  content: string;
  onContentChange: (value: string) => void;
  rationale: string;
  onClose: () => void;
  onCopy: (text: string) => void;
  onCopyAndOpen: (text: string, permalink: string) => void;
  onMarkPosted: (opportunityId: number) => void;
}

/** Side panel showing the original post and the generated reply draft. */
export function OpportunityDetailPanel({
  opportunity,
  content,
  onContentChange,
  rationale,
  onClose,
  onCopy,
  onCopyAndOpen,
  onMarkPosted,
}: OpportunityDetailPanelProps) {
  const [showOriginalThread, setShowOriginalThread] = useState(true);
  const [showRationale, setShowRationale] = useState(false);

  // Reset collapsible state whenever a new opportunity is opened.
  useEffect(() => {
    setShowOriginalThread(true);
    setShowRationale(false);
  }, [opportunity?.id]);

  return (
    <SheetPanel
      title="Reply Draft"
      description={opportunity?.title?.substring(0, 60) || ""}
      open={!!opportunity}
      onOpenChange={(open) => !open && onClose()}
      width="lg"
      footer={
        <div className="flex flex-wrap gap-2">
          <a href="/app/content">
            <Button variant="ghost" size="sm">Review in Studio</Button>
          </a>
          <Button variant="outline" size="sm" onClick={() => onCopy(content)}>
            Copy
          </Button>
          {opportunity?.permalink && (
            <Button size="sm" onClick={() => onCopyAndOpen(content, opportunity.permalink)}>
              Copy &amp; Open Reddit
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => opportunity && onMarkPosted(opportunity.id)}>
            Mark as Posted
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Collapsible: Original Thread */}
        {opportunity?.permalink && (
          <div className="rounded-lg border">
            <button
              type="button"
              onClick={() => setShowOriginalThread(!showOriginalThread)}
              className="flex w-full items-center justify-between p-3 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
            >
              <span>Original Thread</span>
              {showOriginalThread ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            {showOriginalThread && (
              <div className="border-t px-3 pb-3 pt-2">
                <a
                  href={redditUrl(opportunity.permalink)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                >
                  View on Reddit <ExternalLink className="h-3 w-3" />
                </a>
                {opportunity.body_excerpt && (
                  <p className="mt-2 text-xs text-muted-foreground leading-snug">
                    {opportunity.body_excerpt.substring(0, 280)}...
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Draft Textarea */}
        <div className="space-y-2">
          <Label>Generated Response</Label>
          <Textarea
            rows={10}
            value={content}
            onChange={(event) => onContentChange(event.target.value)}
            className="text-sm leading-relaxed"
          />
          <p className="text-xs text-muted-foreground">{content.length} characters</p>
        </div>

        {/* Collapsible: Rationale */}
        {rationale && (
          <div className="rounded-lg border">
            <button
              type="button"
              onClick={() => setShowRationale(!showRationale)}
              className="flex w-full items-center justify-between p-3 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
            >
              <span>Why this response works</span>
              {showRationale ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            {showRationale && (
              <div className="border-t px-3 pb-3 pt-2">
                <p className="text-sm text-muted-foreground">{rationale}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </SheetPanel>
  );
}
