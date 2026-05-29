"use client";

import { useRef, useState, useCallback } from "react";
import { Upload, FileText, Image as ImageIcon, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  accept: string;
  label: string;
  hint: string;
  icon?: "pdf" | "image";
  onFile: (file: File) => void;
}

const SAMPLE_FILES = {
  pdf: [
    { name: "sample-claim-form.pdf", size: "142 KB" },
    { name: "medical-report-injected.pdf", size: "89 KB" },
    { name: "damage-assessment-hidden-text.pdf", size: "213 KB" },
  ],
  image: [
    { name: "damage-photo-clean.jpg", size: "1.2 MB" },
    { name: "receipt-with-steganography.png", size: "445 KB" },
    { name: "qr-payload-embedded.jpg", size: "678 KB" },
  ],
};

export function UploadZone({ accept, label, hint, icon = "pdf", onFile }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const handleFile = useCallback(
    (f: File) => {
      setFile(f);
      onFile(f);
    },
    [onFile]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const Icon = icon === "pdf" ? FileText : ImageIcon;
  const samples = SAMPLE_FILES[icon];

  if (file) {
    return (
      <div className="flex items-center gap-3 rounded border border-ok/40 bg-ok/5 px-4 py-3">
        <Icon className="h-5 w-5 shrink-0 text-ok" />
        <div className="min-w-0 flex-1">
          <div className="truncate font-mono text-xs text-fg-0">{file.name}</div>
          <div className="font-mono text-[10px] text-fg-3">
            {(file.size / 1024).toFixed(0)} KB · ready to submit
          </div>
        </div>
        <button
          type="button"
          onClick={() => setFile(null)}
          className="shrink-0 rounded p-1 text-fg-3 hover:text-fg-0 transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-3 rounded border-2 border-dashed",
          "px-6 py-10 transition-colors",
          dragging
            ? "border-trust bg-trust/5"
            : "border-border hover:border-fg-3 hover:bg-bg-2"
        )}
      >
        <Upload className={cn("h-8 w-8", dragging ? "text-trust" : "text-fg-3")} />
        <div className="text-center">
          <div className="font-mono text-sm text-fg-1">{label}</div>
          <div className="mt-1 font-mono text-xs text-fg-3">{hint}</div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </div>

      {/* sample files */}
      <div>
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-fg-3">
          Sample attack files
        </div>
        <div className="space-y-1">
          {samples.map((s) => (
            <button
              key={s.name}
              type="button"
              onClick={() => {
                const f = new File(["[sample payload]"], s.name, {
                  type: icon === "pdf" ? "application/pdf" : "image/jpeg",
                });
                handleFile(f);
              }}
              className="flex w-full items-center gap-3 rounded px-2 py-1.5 hover:bg-bg-2 transition-colors group"
            >
              <Icon className="h-3.5 w-3.5 shrink-0 text-fg-3 group-hover:text-fg-1 transition-colors" />
              <span className="min-w-0 flex-1 truncate text-left font-mono text-xs text-fg-2 group-hover:text-fg-0 transition-colors">
                {s.name}
              </span>
              <span className="shrink-0 font-mono text-[10px] text-fg-3">{s.size}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
