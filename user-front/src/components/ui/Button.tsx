import React from "react";

type ButtonVariant = "solid" | "ghost";

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: ButtonVariant;
  className?: string;
  type?: "button" | "submit" | "reset";
}

const baseClass =
  "inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm transition active:scale-[.99]";
const variants: Record<ButtonVariant, string> = {
  solid: "bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50",
  ghost: "bg-transparent text-gray-700 hover:bg-gray-100 disabled:opacity-50",
};

export default function Button({
  children,
  onClick,
  disabled,
  variant = "solid",
  className = "",
  type = "button",
}: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClass} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}
