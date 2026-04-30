import { SessionDetailData } from "@/types/session-detail";

function SearchIcon() {
  return <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="5.5" stroke="#64748B" strokeWidth="1.5" /><path d="M12.5 12.5L16 16" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" /></svg>;
}
function HelpIcon() {
  return <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="10" cy="10" r="8.2" stroke="#0F172A" strokeWidth="1.5" /><path d="M7.9 7.8C7.9 6.63 8.88 5.8 10.1 5.8C11.23 5.8 12.1 6.46 12.1 7.56C12.1 8.4 11.66 8.87 10.97 9.28C10.22 9.73 9.9 10.09 9.9 10.9" stroke="#0F172A" strokeWidth="1.5" strokeLinecap="round" /><circle cx="10" cy="13.7" r="0.9" fill="#0F172A" /></svg>;
}
function BellIcon() {
  return <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M6.2 7.7C6.2 5.6 7.9 3.9 10 3.9C12.1 3.9 13.8 5.6 13.8 7.7V9.5C13.8 10.45 14.11 11.38 14.69 12.13L15.4 13.05C15.82 13.6 15.43 14.4 14.74 14.4H5.26C4.57 14.4 4.18 13.6 4.6 13.05L5.31 12.13C5.89 11.38 6.2 10.45 6.2 9.5V7.7Z" stroke="#0F172A" strokeWidth="1.5" /><path d="M8.3 15.2C8.55 16.11 9.2 16.7 10 16.7C10.8 16.7 11.45 16.11 11.7 15.2" stroke="#0F172A" strokeWidth="1.5" strokeLinecap="round" /></svg>;
}

export function SessionDetailTopBar({ data }: { data: SessionDetailData }) {
  return (
    <div className="flex h-[72px] items-center justify-between border-b border-slate-200/90 px-6">
      <div className="flex min-w-0 items-center gap-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-blue-600 text-[21px] font-bold text-white shadow-[0_8px_20px_rgba(37,99,235,0.22)]">e</div>
          <span className="text-[16px] font-semibold tracking-[-0.04em] text-slate-950">Eko</span>
        </div>
        <div className="hidden min-w-0 items-center gap-3 text-[14px] text-slate-500 xl:flex">
          {data.breadcrumb.map((item, index) => <div key={item} className="flex items-center gap-3"><span className={index === data.breadcrumb.length - 1 ? "font-semibold text-slate-800" : ""}>{item}</span>{index < data.breadcrumb.length - 1 && <span className="text-slate-300">/</span>}</div>)}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden h-10 min-w-[332px] items-center gap-3 rounded-[15px] border border-slate-200 bg-white px-4 shadow-[0_4px_12px_rgba(15,23,42,0.03)] lg:flex"><SearchIcon /><span className="flex-1 text-[14px] text-slate-400">搜索（⌘K）</span></div>
        <button className="hidden min-w-[170px] items-center justify-between gap-3 rounded-[16px] border border-slate-200 bg-white px-4 py-2.5 text-left shadow-[0_4px_12px_rgba(15,23,42,0.03)] xl:flex">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-[12px] bg-blue-50 text-blue-600">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path d="M3 5.2L8.4 2.8L15 5.7L9.6 8.1L3 5.2Z" fill="currentColor" fillOpacity="0.18" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                <path d="M3.1 5.7V11.6L9.1 14.3V8.4" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                <path d="M15 5.7V11.2L9.1 14.3" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-[14px] font-semibold text-slate-800">飞书市场部</p>
              <p className="text-[12px] text-slate-500">12 名成员</p>
            </div>
          </div>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4.5 6.5L8 10L11.5 6.5" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <button className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.03)]"><HelpIcon /></button>
        <button className="relative flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white shadow-[0_4px_12px_rgba(15,23,42,0.03)]"><BellIcon /><span className="absolute right-0.5 top-0.5 h-4 min-w-4 rounded-full bg-rose-500 px-1 text-[10px] font-semibold leading-4 text-white">1</span></button>
        <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-[14px] font-semibold text-slate-700 shadow-[0_4px_12px_rgba(15,23,42,0.03)]">SC<span className="absolute bottom-0.5 right-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-500" /></div>
      </div>
    </div>
  );
}
