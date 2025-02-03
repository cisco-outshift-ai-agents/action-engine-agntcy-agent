import { Spinner, SpinnerProps } from "@magnetic/spinner";

interface LoaderProps extends SpinnerProps {}

export const Loader: React.FC<LoaderProps> = ({ ...props }) => {
  return <Spinner size="lg" {...props} />;
};
