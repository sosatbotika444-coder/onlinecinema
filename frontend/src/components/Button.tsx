import clsx from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: ReactNode;
}

export default function Button({ className, variant = "primary", icon, children, ...props }: ButtonProps) {
  return (
    <button className={clsx("ui-button", `ui-button--${variant}`, className)} {...props}>
      {icon}
      {children && <span>{children}</span>}
    </button>
  );
}
