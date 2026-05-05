import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type CardVariant = "default" | "elevated" | "gradient" | "interactive";

const cardVariantClasses: Record<CardVariant, string> = {
  default:
    "rounded-card border border-border bg-card text-card-foreground shadow-sm overflow-hidden",
  elevated:
    "rounded-card border border-border bg-card text-card-foreground shadow-md overflow-hidden",
  gradient:
    "rounded-card border border-border bg-gradient-hero text-card-foreground shadow-sm overflow-hidden",
  interactive:
    "rounded-card border border-border bg-card text-card-foreground shadow-sm overflow-hidden transition hover:border-border-strong hover:shadow-md cursor-pointer"
};

export const Card = forwardRef<
  HTMLElement,
  HTMLAttributes<HTMLElement> & { variant?: CardVariant }
>(({ className, variant = "default", ...props }, ref) => {
  return (
    <section
      ref={ref}
      className={cn(cardVariantClasses[variant], className)}
      {...props}
    />
  );
});
Card.displayName = "Card";

export const CardHeader = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("border-b border-border px-5 py-4", className)}
      {...props}
    />
  );
});
CardHeader.displayName = "CardHeader";

export const CardTitle = forwardRef<
  HTMLHeadingElement,
  HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => {
  return (
    <h2
      ref={ref}
      className={cn(
        "text-sm font-semibold leading-6 text-foreground",
        className
      )}
      {...props}
    />
  );
});
CardTitle.displayName = "CardTitle";

export const CardDescription = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => {
  return (
    <p
      ref={ref}
      className={cn("mt-1 text-xs text-foreground-muted", className)}
      {...props}
    />
  );
});
CardDescription.displayName = "CardDescription";

export const CardContent = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn("p-5", className)} {...props} />;
});
CardContent.displayName = "CardContent";

export const CardFooter = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "flex items-center gap-3 border-t border-border px-5 py-4",
        className
      )}
      {...props}
    />
  );
});
CardFooter.displayName = "CardFooter";
