import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Crosshair, GitBranch, Target, TrendingDown } from "lucide-react";
import KpiCard from "@/components/KpiCard";
import ChartCard from "@/components/ChartCard";
import TimeTabs from "@/components/TimeTabs";
import ExportActions from "@/components/ExportActions";
import { useTenant } from "@/contexts/TenantContext";
import MitreHeatmap from "@/components/MitreHeatmap";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip,
} from "recharts";
import api from "@/api/client";
import { cn } from "@/lib/utils";

const fadeIn = { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 } };

export default function DetectionEngineeringDashboard() {
  const [period, setPeriod] = useState("monthly");
  const { tenantId } = useTenant();
  const { data, isLoading } = useQuery({
    queryKey: ["det-eng", period, tenantId],
    queryFn: async () => (await api.get(`/dashboard/detection-engineering?period=${period}&tenant_id=${tenantId || "all"}`)).data,
    keepPreviousData: true,
  });

  return (
    <motion.div {...fadeIn} className="p-6 md:p-8 space-y-6" data-testid="detection-page">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-bold">Persona</div>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight mt-1" style={{ fontFamily: "var(--font-heading)" }}>
            Detection Engineering
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Detection quality, rule effectiveness and MITRE ATT&CK coverage.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <ExportActions period={period} />
          <TimeTabs value={period} onChange={setPeriod} />
        </div>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <KpiCard label="Detection Coverage" value={data.quality.detection_coverage} suffix="%" icon={Target} delta={2.4} testid="kpi-detection-cov" />
            <KpiCard label="Use Case Coverage" value={data.quality.use_case_coverage} suffix="%" delta={1.1} testid="kpi-usecase-cov" />
            <KpiCard label="MITRE Coverage" value={data.quality.mitre_coverage} suffix="%" testid="kpi-mitre-cov" />
            <KpiCard label="ATLAS Coverage" value={data.quality.atlas_coverage} suffix="%" testid="kpi-atlas" />
            <KpiCard label="Quality Score" value={data.quality.quality_score} testid="kpi-quality-score" />
          </div>

          <ChartCard
            title="MITRE ATT&CK Coverage Heatmap"
            subtitle="Tactics × Techniques"
            testid="chart-mitre-heatmap"
            action={<Badge variant="outline">{data.gap_analysis.techniques_covered} / {data.gap_analysis.techniques_covered + data.gap_analysis.techniques_missing} techniques</Badge>}
          >
            <MitreHeatmap data={data.mitre_heatmap} />
          </ChartCard>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <ChartCard title="Detection Gap Analysis" subtitle="TI + QRadar" testid="chart-gaps" action={<Crosshair className="h-4 w-4 text-muted-foreground" />}>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Techniques Covered</span>
                  <span className="font-semibold tabular">{data.gap_analysis.techniques_covered}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Techniques Missing</span>
                  <span className="font-semibold tabular text-rose-500">{data.gap_analysis.techniques_missing}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">ATLAS Covered</span>
                  <span className="font-semibold tabular">{data.gap_analysis.atlas_covered}</span>
                </div>
                <div className="pt-3 border-t border-border/60">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-bold mb-2">
                    New Detection Opportunities
                  </div>
                  <ul className="space-y-1.5 text-xs">
                    {data.gap_analysis.new_opportunities.map((o) => (
                      <li key={o} className="flex items-start gap-2">
                        <span className="mt-1 h-1 w-1 rounded-full bg-primary shrink-0" />
                        <span>{o}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </ChartCard>

            <ChartCard title="Detection Trends" subtitle="Rules · FP · Coverage" className="lg:col-span-2" testid="chart-det-trends" action={<GitBranch className="h-4 w-4 text-muted-foreground" />}>
              <div className="h-64">
                <ResponsiveContainer>
                  <LineChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                    <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={11} allowDuplicatedCategory={false} type="category" />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                    <Line data={data.trends.new_rules} type="monotone" dataKey="value" name="New Rules" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={false} />
                    <Line data={data.trends.rules_tuned} type="monotone" dataKey="value" name="Rules Tuned" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={false} />
                    <Line data={data.trends.fp_reduction} type="monotone" dataKey="value" name="FP %" stroke="hsl(var(--chart-5))" strokeWidth={2} dot={false} />
                    <Line data={data.trends.coverage_qoq} type="monotone" dataKey="value" name="Coverage %" stroke="hsl(var(--chart-4))" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <Badge variant="outline"><span className="h-2 w-2 rounded-full bg-blue-500 mr-1.5" /> New Rules</Badge>
                <Badge variant="outline"><span className="h-2 w-2 rounded-full bg-emerald-500 mr-1.5" /> Tuned</Badge>
                <Badge variant="outline"><span className="h-2 w-2 rounded-full bg-rose-500 mr-1.5" /> FP</Badge>
                <Badge variant="outline"><span className="h-2 w-2 rounded-full bg-violet-500 mr-1.5" /> Coverage</Badge>
              </div>
            </ChartCard>
          </div>

          <ChartCard title="Rule Effectiveness" subtitle="Precision · Recall · FP" testid="table-rules">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Triggers</TableHead>
                  <TableHead className="text-right">TP</TableHead>
                  <TableHead className="text-right">FP %</TableHead>
                  <TableHead className="text-right">Precision</TableHead>
                  <TableHead className="text-right">Recall</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.rules.map((r) => (
                  <TableRow key={r.name}>
                    <TableCell className="font-medium">{r.name}</TableCell>
                    <TableCell>
                      <Badge variant={r.status === "active" ? "default" : r.status === "tuning" ? "secondary" : "outline"} className="text-[10px]">
                        {r.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular">{r.triggers}</TableCell>
                    <TableCell className="text-right tabular">{r.true_positives}</TableCell>
                    <TableCell className={cn("text-right tabular", r.fp_rate > 40 && "text-rose-500 font-semibold")}>
                      {r.fp_rate}%
                    </TableCell>
                    <TableCell className="text-right tabular">{r.precision}</TableCell>
                    <TableCell className="text-right tabular">{r.recall}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ChartCard>
        </>
      )}
    </motion.div>
  );
}
