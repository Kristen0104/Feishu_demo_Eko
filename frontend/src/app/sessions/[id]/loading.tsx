export default function SessionDetailLoading() {
  return (
    <div className="min-h-dvh bg-[radial-gradient(circle_at_top,_rgba(210,224,255,0.55),_rgba(246,248,252,1)_32%,_rgba(238,243,255,1)_100%)] p-0 lg:px-6 lg:py-4">
      <div className="mx-auto flex min-h-dvh max-w-[1680px] animate-pulse overflow-hidden bg-white/70 lg:min-h-[calc(100vh-32px)] lg:rounded-[34px] lg:border lg:border-slate-200/80">
        <div className="hidden w-[176px] shrink-0 border-r border-slate-200/80 px-3 py-5 lg:block">
          <div className="space-y-3">
            {Array.from({ length: 7 }).map((_, index) => (
              <div key={index} className="h-12 rounded-[18px] bg-slate-100" />
            ))}
          </div>
        </div>
        <div className="flex flex-1 flex-col">
          <div className="h-14 border-b border-slate-200/80 px-3 py-2.5 lg:h-[72px] lg:px-6 lg:py-4">
            <div className="h-9 rounded-2xl bg-slate-100 lg:h-10" />
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-y-auto px-3 py-3 pb-24 lg:px-6 lg:py-6 lg:pb-6 xl:grid-cols-[320px_minmax(0,1fr)_320px]">
            <div className="rounded-[18px] bg-white p-3 lg:rounded-[28px] lg:p-5">
              <div className="h-[420px] rounded-[16px] bg-slate-100 lg:h-full lg:rounded-[22px]" />
            </div>
            <div className="space-y-4">
              <div className="h-28 rounded-[18px] bg-white p-3 lg:h-56 lg:rounded-[28px] lg:p-5"><div className="h-full rounded-[16px] bg-slate-100 lg:rounded-[22px]" /></div>
              <div className="h-[360px] rounded-[18px] bg-white p-3 lg:h-[420px] lg:rounded-[28px] lg:p-5"><div className="h-full rounded-[16px] bg-slate-100 lg:rounded-[22px]" /></div>
            </div>
            <div className="hidden space-y-4 xl:block">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-32 rounded-[28px] bg-white p-5"><div className="h-full rounded-[22px] bg-slate-100" /></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
