// import { useTheme } from "@/hooks/use-theme";
import { useTheme } from "@/hooks/use-theme";
import React from "react";

const MotificLogo: React.FC<MotificLogoProps> = ({ fill, ...props }) => {
  const { resolvedTheme } = useTheme();

  const _fill = fill || (resolvedTheme === "dark" ? "#eee" : "#333");

  return (
    <svg
      id="Motific"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 131.22 112.33"
      {...props}
    >
      <g id="Logo_Grayscale-2" data-name="Logo Grayscale">
        <path
          fill={_fill}
          d="M56.69,110.15c.55.97-.15,2.18-1.27,2.18h-17.87c-4.04,0-7.78-2.16-9.8-5.66L1.21,60.69c-1.62-2.8-1.62-6.25,0-9.05L27.76,5.66C29.78,2.16,33.52,0,37.56,0h17.88C57.76,0,59.21,2.51,58.05,4.53l-28.43,49.25c-1.62,2.8-1.62,6.25,0,9.05l13.28,23.01s0,0,0,0l13.8,24.31ZM85.22,38.14c-.29-.5-1.01-.5-1.3,0l-10.62,18.4c-.27.47-.27,1.05,0,1.52l26.3,46.26c.86,1.52,3.27,2.46,4.19.98.67-1.08,7.36-12.72,9.73-16.85.51-.9.51-1.99,0-2.89l-28.3-47.41ZM130.41,53.15L102.33,4.52C100.71,1.72,97.73,0,94.49,0h-20.41c-3.24,0-6.22,1.72-7.84,4.52l-28.44,49.26c-1.43,2.49-1.59,5.48-.47,8.09l.06.1c.12.29.25.58.41.85l26.57,46.55c1.04,1.82,2.97,2.95,5.07,2.95h23.36c1.12,0,1.82-1.2,1.27-2.17l-27.64-48.23-.03-.04-1.62-2.78c-.53-.91-.53-2.03,0-2.93l18.66-32.89c.29-.5,1.01-.5,1.3.01l32.73,53.87c.56.98,1.97.98,2.53,0l10.39-17.99c1.08-1.87,1.08-4.15,0-6.02Z"
        />
      </g>
    </svg>
  );
};

interface MotificLogoProps extends React.SVGProps<SVGSVGElement> {
  fill?: string;
}

export default MotificLogo;
