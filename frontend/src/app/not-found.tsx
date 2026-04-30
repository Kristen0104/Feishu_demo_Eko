import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-950 px-6 text-center text-slate-200">
      <p className="text-lg font-medium">未找到页面</p>
      <Link href="/" className="text-sky-400 underline underline-offset-4">
        返回首页
      </Link>
    </div>
  );
}
