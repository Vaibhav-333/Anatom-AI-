"use client";
import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import MedicationCard from "@/components/health-tracker/MedicationCard";
import MedicationForm from "@/components/health-tracker/MedicationForm";
import AdherenceChart from "@/components/health-tracker/AdherenceChart";
import ReminderNudge from "@/components/health-tracker/ReminderNudge";
import { PageHero } from "@/components/ui/PageHero";
import { useHealthTrackerStore } from "@/lib/healthTrackerStore";
import { healthTrackerApi } from "@/lib/healthTrackerApi";
import { getLocalUserId } from "@/lib/utils";
import { PAGE_IMAGES } from "@/lib/pageImages";
import { useNotificationStore } from "@/lib/notificationStore";

export default function MedicationsPage() {
  const {
    medications, adherenceStats, todayMedLogs,
    setMedications, addMedication, removeMedication,
    setAdherenceStats, setTodayMedLogs, addMedLog,
  } = useHealthTrackerStore();

  const addNotification = useNotificationStore((s) => s.addNotification);
  const [showForm, setShowForm] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [calendarData, setCalendarData] = useState<{ date: string; taken_count: number; missed_count: number }[]>([]);
  const userId = getLocalUserId();
  const now = new Date();

  useEffect(() => {
    (async () => {
      const [medRes, adhRes, calRes] = await Promise.all([
        healthTrackerApi.getMedications(userId),
        healthTrackerApi.getAdherence(userId),
        healthTrackerApi.getMedCalendar(userId, now.getFullYear(), now.getMonth() + 1),
      ]);
      setMedications(medRes.data);
      setAdherenceStats(adhRes.data);
      setCalendarData(calRes.data);
    })();
  }, [userId]);

  const handleAddMed = async (payload: object) => {
    setFormLoading(true);
    try {
      const res = await healthTrackerApi.addMedication(payload);
      addMedication(res.data);
      setShowForm(false);
      addNotification(
        "medication_added",
        "Medication Added",
        `${res.data.name} (${res.data.dosage}) has been added to your medication schedule.`
      );
    } finally { setFormLoading(false); }
  };

  const handleLogDose = async (medId: string, status: "taken" | "missed") => {
    const res = await healthTrackerApi.logDose({
      medication_id: medId, user_id: userId,
      scheduled_for: new Date().toISOString().slice(0, 19),
      status,
    });
    addMedLog(res.data);
    const adhRes = await healthTrackerApi.getAdherence(userId);
    setAdherenceStats(adhRes.data);
    addNotification(
      "dose_logged",
      status === "taken" ? "Dose Taken ✓" : "Missed Dose Logged",
      status === "taken"
        ? "Your medication dose has been marked as taken. Keep it up!"
        : "Missed dose recorded. Try to stay consistent with your schedule."
    );
  };

  const handleDeactivate = async (medId: string) => {
    await healthTrackerApi.deactivateMedication(medId);
    removeMedication(medId);
  };

  const getTodayStatus = (medId: string): "taken" | "missed" | null => {
    const today = new Date().toISOString().slice(0, 10);
    const log = todayMedLogs.find((l) => l.medication_id === medId && l.date_key === today);
    return (log?.status as "taken" | "missed") ?? null;
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <PageHero src={PAGE_IMAGES.medications} opacity={38} objectPosition="center 50%" accentColor="rgba(0,255,136,0.22)">
        <div className="p-5 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Medications</h1>
            <p className="text-sm text-gray-400 mt-1">Track your medication schedule and adherence.</p>
          </div>
          <button onClick={() => setShowForm(!showForm)}
            className="btn-primary flex items-center gap-2 px-4 py-2 text-sm font-semibold shrink-0">
            <Plus size={14} /> Add Medication
          </button>
        </div>
      </PageHero>

      <ReminderNudge medications={medications} todayLogs={todayMedLogs} />

      {showForm && (
        <MedicationForm userId={userId} onSubmit={handleAddMed} loading={formLoading} onCancel={() => setShowForm(false)} />
      )}

      {calendarData.length > 0 && (
        <div className="rounded-2xl p-5 relative overflow-hidden" style={{ background: "rgba(13,22,39,0.8)", border: "1px solid rgba(0,212,255,0.12)" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={PAGE_IMAGES.medications} alt="" loading="lazy" decoding="async" aria-hidden
            className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
            style={{ opacity: 0.20, objectPosition: "center 50%" }} />
          <div className="absolute inset-0 pointer-events-none"
            style={{ background: "rgba(13,22,39,0.58)" }} />
          <div className="relative">
            <h3 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider mb-4">Adherence This Month</h3>
            <AdherenceChart data={calendarData} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {medications.length === 0 && (
          <p className="col-span-full text-gray-500 text-sm text-center py-8">
            No active medications. Click "Add Medication" to start tracking.
          </p>
        )}
        {medications.map((med) => {
          const adh = adherenceStats.find((a) => a.medication_id === med.id);
          return (
            <MedicationCard
              key={med.id} medication={med} adherence={adh}
              todayStatus={getTodayStatus(med.id)}
              onLogDose={handleLogDose}
              onDeactivate={handleDeactivate}
            />
          );
        })}
      </div>
    </div>
  );
}
