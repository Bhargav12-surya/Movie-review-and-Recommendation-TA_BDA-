import type {SVGProps} from "react";

type IconProps = SVGProps<SVGSVGElement> & {size?: number};

function baseProps(size: number, className?: string): SVGProps<SVGSVGElement> {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
    className: className ? `icon ${className}` : "icon",
  };
}

export function DiscoverIcon({size = 20, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <rect x="3" y="3" width="7" height="7" rx="2" />
      <rect x="14" y="3" width="7" height="7" rx="2" />
      <rect x="3" y="14" width="7" height="7" rx="2" />
      <rect x="14" y="14" width="7" height="7" rx="2" />
    </svg>
  );
}

export function SparkIcon({size = 20, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6z" />
    </svg>
  );
}

export function HeartIcon({size = 20, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z" />
    </svg>
  );
}

export function BookmarkIcon({size = 20, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export function ChatIcon({size = 20, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.5 8.5 0 0 1 8.7 3.9a8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8z" />
    </svg>
  );
}

export function SearchIcon({size = 18, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <circle cx="10.5" cy="10.5" r="7.5" />
      <path d="m16 16 5 5" />
    </svg>
  );
}

export function ArrowIcon({size = 16, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="M5 12h14m-6-6 6 6-6 6" />
    </svg>
  );
}

export function SendIcon({size = 15, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13" />
    </svg>
  );
}

export function InfoIcon({size = 15, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6m0-10v1" />
    </svg>
  );
}

export function CloseIcon({size = 18, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="m6 6 12 12M6 18 18 6" />
    </svg>
  );
}

export function ReviewIcon({size = 18, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="M8 3h11a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8z" />
      <path d="M8 3v5H3m5 5h8m-8 4h6" />
    </svg>
  );
}

export function StarIcon({size = 13, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="m12 3 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3L12 17.4l-5.6 3 1.1-6.3-4.6-4.5 6.3-.9z" />
    </svg>
  );
}

export function CheckIcon({size = 16, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="m5 12 4 4L19 6" />
    </svg>
  );
}

export function PlusIcon({size = 16, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function MicIcon({size = 16, className, ...props}: IconProps) {
  return (
    <svg {...baseProps(size, className)} {...props}>
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8" />
    </svg>
  );
}

