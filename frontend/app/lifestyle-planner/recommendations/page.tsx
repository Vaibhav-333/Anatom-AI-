"use client";
import { useEffect, useState } from "react";
import PreventiveCareCard from "@/components/lifestyle-planner/PreventiveCareCard";
import LifestylePlannerForm from "@/components/lifestyle-planner/LifestylePlannerForm";
import ShareLifestyleReportModal from "@/components/lifestyle-planner/ShareLifestyleReportModal";
import { PageHero } from "@/components/ui/PageHero";
import { useLifestyleStore, LifestylePlanRequest } from "@/lib/lifestyleStore";
import { lifestyleApi } from "@/lib/lifestyleApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { Share2, RefreshCw } from "lucide-react";

export default function RecommendationsPage() {
  const { latestPlan, isGenerating, setLatestPlan, setGenerating, formValues, setFormValues } = useLifestyleStore();
  const [shareOpen, setShareOpen] = useState(false);
  const userId = getLocalUserId();

  useEffect(() => {
    if (!latestPlan) {
      lifestyleApi.getLatestPlan(userId).then((r) => setLatestPlan(r.data)).catch(() => {});
    }
  }, [userId]);

  const handleGenerate = async (req: LifestylePlanRequest) => {
    setGenerating(true);
    setFormValues(req);
    try {
      const res = await lifestyleApi.generatePlan(req);
      setLatestPlan(res.data);
    } finally { setGenerating(false); }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <PageHero src={PAGE_IMAGES.recommendations} opacity={38} objectPosition="center 25%" accentColor="rgba(167,139,250,0.25)">
        <div className="p-5 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Recommendations</h1>
            <p className="text-sm text-gray-400 mt-1">Preventive care and lifestyle adjustments tailored to your condition.</p>
          </div>
          {latestPlan && (
            <button onClick={() => setShareOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium shrink-0"
              style={{ background: "rgba(0,255,136,0.12)", color: "#00FF88", border: "1px solid rgba(0,255,136,0.3)" }}>
              <Share2 size={13} /> Share Plan
            </button>
          )}
        </div>
      </PageHero>

      {latestPlan && (
        <>
          <PreventiveCareCard items={latestPlan.preventive_care ?? []} />
          {latestPlan.ai_notes && (
            <div className="rounded-2xl p-5"
              style={{ background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.2)" }}>
              <p className="text-sm font-semibold text-purple-400 mb-2">AI Notes</p>
              <p className="text-sm text-gray-300">{latestPlan.ai_notes}</p>
            </div>
          )}
        </>
      )}

      <div className="rounded-2xl p-5"
        style={{ background: "rgba(13,22,39,0.8)", border: "1px solid rgba(0,212,255,0.12)" }}>
        <div className="flex items-center gap-2 mb-4">
          <RefreshCw size={14} className="text-cyan-400" />
          <h3 className="text-sm font-semibold text-cyan-400">Update Your Plan</h3>
        </div>
        <LifestylePlannerForm
          userId={userId}
          onGenerate={handleGenerate}
          loading={isGenerating}
          initialValues={formValues ?? undefined}
        />
      </div>

      <ShareLifestyleReportModal userId={userId} open={shareOpen} onClose={() => setShareOpen(false)} />
    </div>
  );
}
