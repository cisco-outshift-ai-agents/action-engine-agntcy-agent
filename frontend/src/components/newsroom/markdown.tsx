import ReactMarkdown from "react-markdown";
import "@/components/newsroom/newsroom-styles/markdown.css";

const Markdown: React.FC<{ children: string | null | undefined }> = ({
  children,
}) => (
  <ReactMarkdown className="newsroom-markdown-body">
    {children || ""}
  </ReactMarkdown>
);

export default Markdown;
