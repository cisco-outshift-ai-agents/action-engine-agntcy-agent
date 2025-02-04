import { Layout } from "@/components/ui/layout/page";
import TextareaAutosize from "react-textarea-autosize";
import { Paperclip, PaperPlaneRight } from "@magnetic/icons";
import { Container } from "@magnetic/container";
import { Flex } from "@magnetic/flex";
import { Button } from "@magnetic/button";
import { cn } from "@/utils";

const SessionPage = () => {
  return (
    <Layout>
      <Container className="h-full">
        <Flex
          direction="vertical"
          className="h-full rounded-lg border border-white/10 bg-[#32363c]"
        >
          <div className="flex-1" />

          <div className="px-4 pt-2 pb-3">
            <Flex
              as="form"
              align="center"
              className="max-w-3xl mx-auto bg-[#373c42] border border-[#666666] p-3 rounded-lg"
            >
              <Button
                type="button"
                kind="tertiary"
                icon={<Paperclip />}
                className="hover:opacity-80 px-2"
              />

              <TextareaAutosize
                minRows={1}
                maxRows={8}
                placeholder="What do you want ActionEngine to do?"
                className={cn(
                  "w-full bg-transparent text-white",
                  "font-normal text-base leading-[22px]",
                  "placeholder:text-grey-400 placeholder:text-sm",
                  "focus:outline-none resize-none"
                )}
                wrap="hard"
              />

              <Button
                type="submit"
                kind="tertiary"
                icon={<PaperPlaneRight />}
                className="hover:opacity-80 px-2"
              />
            </Flex>
          </div>
        </Flex>
      </Container>
    </Layout>
  );
};

export default SessionPage;
