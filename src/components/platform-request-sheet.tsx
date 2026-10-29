"use client";

import { useState } from "react";
import { CheckCircle2Icon } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PLATFORMS } from "@/lib/campaigns";

type Status = { kind: "idle" } | { kind: "sending" } | { kind: "sent" } | { kind: "error"; message: string };

/** "이 체험단 사이트도 모아주세요" 요청 폼 → /api/platform-requests (DB 저장 + 운영자 메일) */
export function PlatformRequestSheet({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [siteName, setSiteName] = useState("");
  const [siteUrl, setSiteUrl] = useState("");
  const [note, setNote] = useState("");
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState(""); // 봇 방지용 숨은 칸
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  function handleOpenChange(next: boolean) {
    // 보낸 뒤 닫으면 다음에 열 때 빈 폼으로 (메일 주소는 다음 요청에도 쓰도록 남겨둔다)
    if (!next && status.kind === "sent") {
      setStatus({ kind: "idle" });
      setSiteName("");
      setSiteUrl("");
      setNote("");
    }
    onOpenChange(next);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus({ kind: "sending" });
    try {
      const res = await fetch("/api/platform-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ siteName, siteUrl, note, email, website }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setStatus({ kind: "error", message: data.error ?? "요청을 보내지 못했어요. 잠시 후 다시 시도해 주세요." });
        return;
      }
      setStatus({ kind: "sent" });
    } catch {
      setStatus({ kind: "error", message: "인터넷 연결을 확인하고 다시 시도해 주세요." });
    }
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="bottom" className="mx-auto max-h-[90vh] max-w-md gap-0 rounded-t-2xl">
        <SheetHeader className="pb-1">
          <SheetTitle>체험단 사이트 추가 요청</SheetTitle>
        </SheetHeader>

        {status.kind === "sent" ? (
          <div className="flex flex-col items-center gap-3 px-6 pt-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] text-center">
            <CheckCircle2Icon className="size-10 text-primary" />
            <div>
              <p className="font-medium text-foreground">요청을 보냈어요</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {email
                  ? "검토 후 추가되면 남겨주신 메일로 알려드릴게요."
                  : "검토 후 BLEACH에 추가되면 목록에서 바로 볼 수 있어요."}
              </p>
            </div>
            <Button className="mt-2 w-full" onClick={() => handleOpenChange(false)}>
              확인
            </Button>
          </div>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-4 overflow-y-auto px-4 pt-2 pb-[max(1rem,env(safe-area-inset-bottom))]">
            <p className="text-sm text-muted-foreground">
              지금은 {PLATFORMS.join(" · ")}의 체험단을 모아요. 자주 쓰는 다른 사이트가 있다면 알려주세요.
            </p>

            <Field label="사이트 이름" htmlFor="pr-name" required>
              <Input
                id="pr-name"
                value={siteName}
                onChange={(e) => setSiteName(e.target.value)}
                placeholder="예) 강남맛집, 디너의여왕"
                maxLength={100}
                required
                className="h-10"
              />
            </Field>
            <Field label="사이트 주소" htmlFor="pr-url">
              <Input
                id="pr-url"
                value={siteUrl}
                onChange={(e) => setSiteUrl(e.target.value)}
                placeholder="www.example.com"
                inputMode="url"
                autoCapitalize="none"
                maxLength={500}
                className="h-10"
              />
            </Field>
            <Field label="하고 싶은 말" htmlFor="pr-note">
              <textarea
                id="pr-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="어떤 체험단이 많은 곳인지 알려주시면 우선순위를 정하는 데 도움이 돼요."
                maxLength={1000}
                rows={3}
                className="w-full resize-none rounded-lg border border-input bg-transparent px-2.5 py-2 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
              />
            </Field>
            <Field label="답장 받을 메일" htmlFor="pr-email" hint="선택 · 추가되면 알려드려요">
              <Input
                id="pr-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="me@example.com"
                autoCapitalize="none"
                maxLength={200}
                className="h-10"
              />
            </Field>
            {/* 봇 방지: 화면·스크린리더 모두에서 숨김 */}
            <input
              type="text"
              tabIndex={-1}
              autoComplete="off"
              aria-hidden
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              className="hidden"
              name="website"
            />

            {status.kind === "error" && (
              <p role="alert" className="text-sm text-destructive">
                {status.message}
              </p>
            )}
            <Button type="submit" className="h-11" disabled={!siteName.trim() || status.kind === "sending"}>
              {status.kind === "sending" ? "보내는 중…" : "요청 보내기"}
            </Button>
          </form>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Field({
  label,
  htmlFor,
  hint,
  required,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">
        {label}
        {required && <span className="ml-0.5 text-primary">*</span>}
        {hint && <span className="ml-1.5 text-xs font-normal text-muted-foreground">{hint}</span>}
      </label>
      {children}
    </div>
  );
}
