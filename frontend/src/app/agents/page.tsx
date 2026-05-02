import { redirect } from "next/navigation";

/** 旧「Agents」入口并入「应用」工作台 */
export default function AgentsRedirectPage() {
  redirect("/apps");
}
