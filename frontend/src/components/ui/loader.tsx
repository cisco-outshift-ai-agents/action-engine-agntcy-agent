interface LoaderProps extends React.ImgHTMLAttributes<HTMLImageElement> {}
import LoaderImage from "@/assets/images/loader.gif";

export const Loader: React.FC<LoaderProps> = (props) => {
  return (
    <div className="flex items-center justify-center">
      <img src={LoaderImage} {...props} />
    </div>
  );
};
