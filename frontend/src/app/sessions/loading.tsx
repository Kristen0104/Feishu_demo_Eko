export default function SessionsLoading() {
  return (
    <div className="min-h-dvh overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(210,224,255,0.55),_rgba(246,248,252,1)_32%,_rgba(238,243,255,1)_100%)] p-0 lg:px-6 lg:py-4">
      <div className="mx-auto flex min-h-dvh max-w-[1680px] animate-pulse overflow-hidden bg-white/70 lg:min-h-[calc(100vh-32px)] lg:rounded-[34px] lg:border lg:border-slate-200/80">
        <div className="hidden w-[230px] shrink-0 border-r border-slate-200/80 bg-white/70 px-6 py-6 lg:block">
          <div className="h-12 w-28 rounded-2xl bg-slate-100" />
          <div className="mt-8 space-y-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-12 rounded-[18px] bg-slate-100" />
            ))}
          </div>
        </div>
        <div className="flex flex-1 flex-col">
          <div className="h-14 border-b border-slate-200/80 px-3 py-2.5 lg:h-[86px] lg:px-8 lg:py-5">
            <div className="h-9 w-full rounded-2xl bg-slate-100 lg:h-10" />
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-y-auto px-3 py-3 pb-24 lg:gap-6 lg:px-8 lg:py-6 lg:pb-6 xl:grid-cols-[minmax(0,1fr)_392px]">
            <div className="rounded-[18px] bg-white p-3 shadow-[0_12px_32px_rgba(100,116,139,0.08)] lg:rounded-[28px] lg:p-6">
              <div className="h-11 w-full rounded-2xl bg-slate-100" />
              <div className="mt-5 space-y-3">
                {Array.from({ length: 7 }).map((_, index) => (
                  <div key={index} className="h-24 rounded-[22px] bg-slate-100" />
                ))}
              </div>
            </div>
            <div className="hidden rounded-[28px] bg-white p-6 shadow-[0_12px_32px_rgba(100,116,139,0.08)] xl:block">
              <div className="h-8 w-40 rounded-xl bg-slate-100" />
              <div className="mt-6 space-y-4">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={index} className="h-24 rounded-[20px] bg-slate-100" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
