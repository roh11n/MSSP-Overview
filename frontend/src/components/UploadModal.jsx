import { useRef, useState } from "react";
import { Upload, FileSpreadsheet, X, Check } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import api from "@/api/client";
import { cn } from "@/lib/utils";
import { useTenant } from "@/contexts/TenantContext";

export default function UploadModal({ open, onOpenChange }) {
  const [source, setSource] = useState("qradar");
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [result, setResult] = useState(null);
  const [uploading, setUploading] = useState(false);
  const { tenantId, tenant } = useTenant();
  const inputRef = useRef(null);

  const reset = () => { setFile(null); setResult(null); };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const tid = tenantId || "all";
      const { data } = await api.post(
        `/upload/data?source=${source}&tenant_id=${encodeURIComponent(tid)}`,
        form,
      );
      setResult(data);
      const suffix = source === "threat_intel" && data.ti_row_count
        ? ` · ${data.ti_row_count} advisory rows bound to Threat Intelligence`
        : "";
      toast.success(`Ingested ${data.rows} rows from ${data.filename}${suffix}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}
    >
      <DialogContent className="max-w-lg" data-testid="upload-modal">
        <DialogHeader>
          <DialogTitle>Upload Data Source</DialogTitle>
          <DialogDescription>
            Ingest CSV or Excel from QRadar, XSOAR, or Threat Intelligence exports.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground">
              Source
            </label>
            <Select value={source} onValueChange={setSource}>
              <SelectTrigger className="mt-2" data-testid="upload-source-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="qradar">QRadar (Offenses / Events / Rules)</SelectItem>
                <SelectItem value="xsoar">XSOAR (Incidents / Playbooks / Analysts)</SelectItem>
                <SelectItem value="threat_intel">Threat Intel (Advisories / CVE / IOC)</SelectItem>
              </SelectContent>
            </Select>
            {source === "threat_intel" && (
              <div className="mt-2 rounded-md border border-primary/30 bg-primary/5 p-2 text-[11px] text-muted-foreground leading-relaxed" data-testid="upload-hint-threat-intel">
                <span className="font-semibold text-foreground">Expected columns:</span> Advisories Name, Industry, Date of Release, IPs, Domain, Hash, Hash Type. Uploading replaces prior data for tenant <span className="font-semibold text-foreground">{tenant?.name || "All Tenants"}</span> and drives the Threat Intelligence dashboard live.
              </div>
            )}
          </div>

          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
            }}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "cursor-pointer border-2 border-dashed rounded-lg p-6 text-center transition-colors",
              dragOver ? "border-primary bg-primary/5" : "border-border/60 hover:border-primary/60",
            )}
            data-testid="upload-dropzone"
          >
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              data-testid="upload-file-input"
            />
            {file ? (
              <div className="flex items-center justify-center gap-2 text-sm">
                <FileSpreadsheet className="h-5 w-5 text-primary" />
                <span className="font-medium">{file.name}</span>
                <Badge variant="secondary">{(file.size / 1024).toFixed(1)} KB</Badge>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="ml-2 rounded-full p-1 hover:bg-muted"
                  data-testid="upload-clear-file"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <div className="text-sm font-medium">Drop CSV or Excel file here</div>
                <div className="text-xs text-muted-foreground mt-1">or click to browse</div>
              </>
            )}
          </div>

          {result && (
            <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
              <div className="flex items-center gap-2 font-medium text-emerald-500">
                <Check className="h-4 w-4" /> Ingestion complete
              </div>
              <div className="mt-2 text-xs text-muted-foreground space-y-1">
                <div>Rows: <span className="text-foreground font-medium">{result.rows}</span></div>
                <div>Columns: {result.columns?.slice(0, 6).join(", ")}{result.columns?.length > 6 ? "…" : ""}</div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="upload-cancel-btn">
              Close
            </Button>
            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              data-testid="upload-submit-btn"
            >
              {uploading ? "Uploading…" : "Ingest"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
