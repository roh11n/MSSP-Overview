import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { Plus, Upload, Palette, Building2, Image as ImageIcon, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/api/client";
import { useTenant } from "@/contexts/TenantContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";

const fadeIn = { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 } };

export default function SettingsPage() {
  const { tenants, refresh } = useTenant();
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#3B82F6");
  const [logoUrl, setLogoUrl] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [newDomain, setNewDomain] = useState("");
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#3B82F6");
  const [uploading, setUploading] = useState(false);
  const [csvUploading, setCsvUploading] = useState(false);
  const logoInputRef = useRef(null);
  const csvInputRef = useRef(null);
  const [aiStatus, setAiStatus] = useState(null);

  useEffect(() => {
    if (!selected && tenants.length) setSelected(tenants[0]);
  }, [tenants, selected]);

  useEffect(() => {
    if (selected) {
      setName(selected.name || "");
      setDescription(selected.description || "");
      setPrimaryColor(selected.primary_color || "#3B82F6");
      setLogoUrl(selected.logo_url || null);
    }
  }, [selected]);

  useEffect(() => {
    api.get("/ai/status").then((r) => setAiStatus(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    try {
      const { data } = await api.patch(`/tenants/${selected.id}`, {
        name, description, primary_color: primaryColor,
      });
      toast.success("Tenant updated");
      setSelected(data);
      refresh();
    } catch (e) {
      toast.error("Save failed");
    }
  };

  const uploadLogo = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post(`/tenants/${selected.id}/logo`, form);
      toast.success("Logo uploaded");
      // Refresh to load new data URL
      const { data: fresh } = await api.get("/tenants");
      const found = fresh.find((t) => t.id === selected.id);
      setSelected(found);
      refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Logo upload failed");
    } finally {
      setUploading(false);
    }
  };

  const createTenant = async () => {
    if (!newDomain || !newName) { toast.error("Domain + name required"); return; }
    try {
      await api.post("/tenants", {
        domain: newDomain, name: newName, primary_color: newColor,
      });
      toast.success(`Tenant "${newName}" added`);
      setAddOpen(false); setNewDomain(""); setNewName(""); setNewColor("#3B82F6");
      refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Create failed");
    }
  };

  const uploadCsv = async (file) => {
    if (!file) return;
    setCsvUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/tenants/upload-csv", form);
      toast.success(`Imported ${data.added} of ${data.total_rows} tenants from CSV`);
      refresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "CSV import failed");
    } finally {
      setCsvUploading(false);
    }
  };

  return (
    <motion.div {...fadeIn} className="p-6 md:p-8 space-y-6" data-testid="settings-page">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-bold">Console</div>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight mt-1" style={{ fontFamily: "var(--font-heading)" }}>
            Settings · Tenants & Branding
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Manage QRadar domains, per-tenant white-label branding, and review AI model status.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={(e) => uploadCsv(e.target.files?.[0])}
            data-testid="tenant-csv-input"
          />
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => csvInputRef.current?.click()}
            disabled={csvUploading}
            data-testid="tenant-csv-upload"
          >
            <Upload className="h-4 w-4" />
            {csvUploading ? "Importing…" : "Import from QRadar CSV"}
          </Button>
          <Button onClick={() => setAddOpen(true)} size="sm" className="gap-2" data-testid="add-tenant-btn">
            <Plus className="h-4 w-4" />
            Add Tenant
          </Button>
        </div>
      </div>

      {/* AI Model status card */}
      {aiStatus && (
        <Card className="p-4 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${aiStatus.loaded ? "bg-emerald-500" : aiStatus.loading ? "bg-amber-500 animate-pulse" : "bg-rose-500"}`} />
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground">
              HuggingFace LLM
            </span>
          </div>
          <div className="text-sm font-mono">{aiStatus.model}</div>
          <Badge variant={aiStatus.loaded ? "default" : "secondary"} className="text-[10px]">
            {aiStatus.loaded ? "READY" : aiStatus.loading ? "LOADING" : "IDLE"}
          </Badge>
          {aiStatus.error && <span className="text-xs text-rose-500">{aiStatus.error}</span>}
          <span className="text-xs text-muted-foreground ml-auto">
            Powers reasoning & justification on Executive Overview + PPTX exports.
          </span>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tenant list */}
        <Card className="p-4 space-y-2 lg:col-span-1" data-testid="tenant-list">
          <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground px-2 py-1">
            Tenants ({tenants.length})
          </div>
          {tenants.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelected(t)}
              className={`w-full text-left rounded-md border px-3 py-2 transition-colors ${
                selected?.id === t.id
                  ? "border-primary bg-accent"
                  : "border-border/60 hover:bg-accent/50"
              }`}
              data-testid={`tenant-list-${t.id}`}
            >
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: t.primary_color }} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{t.name}</div>
                  <div className="text-[10px] font-mono text-muted-foreground truncate">{t.domain}</div>
                </div>
              </div>
            </button>
          ))}
        </Card>

        {/* Tenant editor */}
        {selected ? (
          <Card className="p-6 space-y-5 lg:col-span-2" data-testid="tenant-editor">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground">Editing</div>
                <h2 className="text-2xl font-bold tracking-tight" style={{ fontFamily: "var(--font-heading)" }}>
                  {selected.name}
                </h2>
                <div className="text-xs font-mono text-muted-foreground mt-1">
                  QRadar Domain: {selected.domain}
                </div>
              </div>
              <Badge variant="outline">{selected.id}</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit-name">Display Name</Label>
                <Input id="edit-name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5" data-testid="edit-tenant-name" />
              </div>
              <div>
                <Label htmlFor="edit-color">Primary Color</Label>
                <div className="mt-1.5 flex items-center gap-2">
                  <input
                    id="edit-color"
                    type="color"
                    value={primaryColor}
                    onChange={(e) => setPrimaryColor(e.target.value)}
                    className="h-10 w-16 rounded-md border border-border/60 bg-transparent cursor-pointer"
                    data-testid="edit-tenant-color"
                  />
                  <Input value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="flex-1 font-mono text-xs" />
                </div>
              </div>
            </div>

            <div>
              <Label htmlFor="edit-desc">Description</Label>
              <Textarea id="edit-desc" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className="mt-1.5" data-testid="edit-tenant-desc" />
            </div>

            <div>
              <Label>Logo (used in PPTX cover)</Label>
              <div className="mt-2 flex items-center gap-4">
                <div className="h-20 w-20 rounded-md border border-border/60 bg-muted/30 grid place-items-center overflow-hidden">
                  {logoUrl ? (
                    <img src={logoUrl} alt="tenant logo" className="max-h-full max-w-full object-contain" />
                  ) : (
                    <ImageIcon className="h-6 w-6 text-muted-foreground" />
                  )}
                </div>
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => uploadLogo(e.target.files?.[0])}
                  data-testid="edit-logo-input"
                />
                <div>
                  <Button onClick={() => logoInputRef.current?.click()} variant="outline" disabled={uploading} className="gap-2" data-testid="edit-logo-btn">
                    <Upload className="h-4 w-4" /> {uploading ? "Uploading…" : "Upload Logo"}
                  </Button>
                  <div className="text-[10px] text-muted-foreground mt-1">PNG or SVG, &lt; 512 KB</div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border/60">
              <Button onClick={save} className="gap-2" data-testid="save-tenant-btn">
                <Save className="h-4 w-4" /> Save Changes
              </Button>
            </div>
          </Card>
        ) : (
          <Card className="p-10 text-center text-sm text-muted-foreground lg:col-span-2">
            Select a tenant to edit branding.
          </Card>
        )}
      </div>

      {/* Add tenant dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-w-md" data-testid="add-tenant-modal">
          <DialogHeader>
            <DialogTitle>Add QRadar Tenant</DialogTitle>
            <DialogDescription>Create a new tenant scoped to a QRadar domain.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="new-name">Tenant Name</Label>
              <Input id="new-name" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Contoso Ltd" className="mt-1.5" data-testid="new-tenant-name" />
            </div>
            <div>
              <Label htmlFor="new-domain">QRadar Domain</Label>
              <Input id="new-domain" value={newDomain} onChange={(e) => setNewDomain(e.target.value)} placeholder="CONTOSO_LTD" className="mt-1.5 font-mono" data-testid="new-tenant-domain" />
            </div>
            <div>
              <Label htmlFor="new-color">Brand Color</Label>
              <div className="mt-1.5 flex items-center gap-2">
                <input id="new-color" type="color" value={newColor} onChange={(e) => setNewColor(e.target.value)} className="h-10 w-16 rounded-md border border-border/60 cursor-pointer" data-testid="new-tenant-color" />
                <Input value={newColor} onChange={(e) => setNewColor(e.target.value)} className="flex-1 font-mono text-xs" />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
              <Button onClick={createTenant} data-testid="create-tenant-submit">Create</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
