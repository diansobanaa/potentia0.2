 
// Lokasi: src/shared/ui/Button.tsx

import { TouchableOpacity, Text, TouchableOpacityProps } from "react-native";
import { cva, type VariantProps } from "class-variance-authority";

// --- CVA (Class Variance Authority) ---
// Ini adalah best practice untuk membuat varian tombol dengan NativeWind

const buttonVariants = cva(
  "w-full justify-center items-center rounded-full py-4", // Style dasar
  {
    variants: {
      variant: {
        // Tombol putih (seperti "Next")
        primary: "bg-white active:bg-neutral-200",
        // Tombol border putih (seperti "Forgot password?")
        outline: "bg-transparent border border-neutral-700 active:bg-neutral-800",
      },
      disabled: {
        true: "bg-neutral-700",
      },
    },
    defaultVariants: {
      variant: "primary",
    },
  }
);

const textVariants = cva("text-lg font-bold", { // Style teks dasar
  variants: {
    variant: {
      primary: "text-black", // Teks hitam untuk tombol putih
      outline: "text-white", // Teks putih untuk tombol outline
    },
    disabled: {
      true: "text-neutral-400",
    },
  },
  defaultVariants: {
    variant: "primary",
  },
});

// Definisikan props
export interface ButtonProps
  extends TouchableOpacityProps,
    VariantProps<typeof buttonVariants> {
  title: string;
}

export function Button({
  className,
  variant,
  title,
  disabled,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || false;
  
  return (
    <TouchableOpacity
      className={buttonVariants({ variant, disabled: isDisabled, className })}
      disabled={isDisabled}
      {...props}
    >
      <Text className={textVariants({ variant, disabled: isDisabled })}>
        {title}
      </Text>
    </TouchableOpacity>
  );
}