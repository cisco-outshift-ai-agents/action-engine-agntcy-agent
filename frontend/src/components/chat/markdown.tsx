import ReactMarkdown from "react-markdown";
import "@/components/chat/chat-styles/markdown.css";

const Markdown: React.FC<{ children: string | null | undefined }> = ({
  children,
}) => (
  <ReactMarkdown className="chat-markdown-body">{children || ""}</ReactMarkdown>
);

export default Markdown;
