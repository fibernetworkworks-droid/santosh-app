import * as React from "react";
import * as NavigationMenuPrimitive from "@radix-ui/react-navigation-menu";
import { cva } from "class-variance-authority";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export const NavigationMenu = React.forwardRef<
  React.ElementRef<typeof NavigationMenuPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof NavigationMenuPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <NavigationMenuPrimitive.Root
    ref={ref}
    className={cn("relative z-10 flex max-w-max flex-1 items-center justify-center", className)}
    {...props}
  >
    {children}
    <NavigationMenuViewport />
  </NavigationMenuPrimitive.Root>
));
NavigationMenu.displayName = "NavigationMenu";

export const NavigationMenuList = React.forwardRef<
  React.ElementRef<typeof NavigationMenuPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof NavigationMenuPrimitive.List>
>(({ className, ...props }, ref) => (
  <NavigationMenuPrimitive.List
    ref={ref}
    className={cn("group flex flex-1 list-none items-center justify-center gap-1", className)}
    {...props}
  />
));
NavigationMenuList.displayName = "NavigationMenuList";

export const NavigationMenuItem = NavigationMenuPrimitive.Item;

export const navigationMenuTriggerStyle = cva(
  "group inline-flex h-10 w-max items-center justify-center rounded-control bg-surface px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-primary/10 focus:bg-primary/10 focus:outline-none disabled:pointer-events-none disabled:opacity-50 data-[active]:bg-primary/10 data-[state=open]:bg-primary/10",
);

export const NavigationMenuTrigger = React.forwardRef<
  React.ElementRef<typeof NavigationMenuPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof NavigationMenuPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <NavigationMenuPrimitive.Trigger ref={ref} className={cn(navigationMenuTriggerStyle(), "group", className)} {...props}>
    {children}{" "}
    <ChevronDown
      className="relative top-px ml-1 size-3 transition-transform duration-200 group-data-[state=open]:rotate-180"
      aria-hidden="true"
    />
  </NavigationMenuPrimitive.Trigger>
));
NavigationMenuTrigger.displayName = "NavigationMenuTrigger";

export const NavigationMenuContent = React.forwardRef<
  React.ElementRef<typeof NavigationMenuPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof NavigationMenuPrimitive.Content>
>(({ className, ...props }, ref) => (
  <NavigationMenuPrimitive.Content
    ref={ref}
    className={cn("left-0 top-0 w-full data-[motion]:animate-fade-in md:absolute md:w-auto", className)}
    {...props}
  />
));
NavigationMenuContent.displayName = "NavigationMenuContent";

export const NavigationMenuLink = NavigationMenuPrimitive.Link;

export const NavigationMenuViewport = React.forwardRef<
  React.ElementRef<typeof NavigationMenuPrimitive.Viewport>,
  React.ComponentPropsWithoutRef<typeof NavigationMenuPrimitive.Viewport>
>(({ className, ...props }, ref) => (
  <div className="absolute left-0 top-full flex justify-center">
    <NavigationMenuPrimitive.Viewport
      ref={ref}
      className={cn(
        "relative z-50 mt-1.5 h-(--radix-navigation-menu-viewport-height) w-full origin-top overflow-hidden rounded-card border border-line bg-surface text-ink shadow-card data-[state=open]:animate-fade-in md:w-(--radix-navigation-menu-viewport-width)",
        className,
      )}
      {...props}
    />
  </div>
));
NavigationMenuViewport.displayName = "NavigationMenuViewport";

export const NavigationMenuIndicator = React.forwardRef<
  React.ElementRef<typeof NavigationMenuPrimitive.Indicator>,
  React.ComponentPropsWithoutRef<typeof NavigationMenuPrimitive.Indicator>
>(({ className, ...props }, ref) => (
  <NavigationMenuPrimitive.Indicator
    ref={ref}
    className={cn(
      "top-full z-10 flex h-1.5 items-end justify-center overflow-hidden data-[state=visible]:animate-fade-in",
      className,
    )}
    {...props}
  >
    <div className="relative top-3/5 size-2 rotate-45 rounded-tl-control bg-line shadow-card" />
  </NavigationMenuPrimitive.Indicator>
));
NavigationMenuIndicator.displayName = "NavigationMenuIndicator";
