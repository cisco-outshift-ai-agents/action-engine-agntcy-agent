import { Layout } from "@/components/ui/layout/page";
import { Container } from "@magnetic/container";
import { Text } from "@magnetic/text";

const PlaceholderPage = () => {
  return (
    <Layout>
      <Container className="flex items-center justify-center h-full">
        <Text size="p2" weight="bold" color="light">
          This page has not been implemented yet. This is a placeholder page.
        </Text>
      </Container>
    </Layout>
  );
};

export default PlaceholderPage;
