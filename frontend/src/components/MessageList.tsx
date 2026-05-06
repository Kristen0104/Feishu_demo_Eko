import { ScenarioData } from "@/types/workspace";

import { MessageBubble } from "./MessageBubble";

export function MessageList({ scenario }: { scenario: ScenarioData }) {
  return (
    <div className="space-y-4">
      {scenario.messages.map((message) => (
        <MessageBubble key={message.id} message={message} scenario={scenario} />
      ))}
    </div>
  );
}
