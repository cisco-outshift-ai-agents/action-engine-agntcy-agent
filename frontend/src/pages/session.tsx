import { Layout } from "@/components/ui/layout/page";
import TextareaAutosize from "react-textarea-autosize";
import { Paperclip, PaperPlaneRight } from "@magnetic/icons";
import { cn } from "@/utils";

const SessionPage = () => {
  return (
    <Layout>
      <div className="flex flex-col h-full rounded-lg border border-white/10 bg-[#373c42]">
        <div className="flex-1" />

        <div className="px-4 pt-2 pb-3">
          <form className="flex items-center max-w-3xl mx-auto bg-[#0f1214] border border-[#666666] p-3 rounded-lg">
            <button
              type="button"
              className="flex items-center text-white hover:opacity-80 px-2"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            <TextareaAutosize
              minRows={1}
              maxRows={3}
              placeholder="What do you want ActionEngine to do?"
              className={cn(
                "w-[968px] bg-transparent",
                "font-normal text-base leading-[22px]",
                "placeholder:text-[#AAAAAA] placeholder:font-inter placeholder:font-normal",
                "focus:outline-none resize-none"
              )}
            />

            <button
              type="submit"
              className="flex items-center text-white hover:opacity-80 px-2"
            >
              <PaperPlaneRight className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </Layout>
  );
};

export default SessionPage;
