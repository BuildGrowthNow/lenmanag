/**
 * esbuild plugin to provide virtual modules for shadcn/ui components.
 * This allows generated code to import from '@/components/ui/*' paths.
 */

import type { Plugin } from 'esbuild';

/**
 * Inline shadcn component implementations.
 * These are bundled directly into the generated code.
 */
const SHADCN_UTILS = `
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
`;

const SHADCN_BUTTON = `
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const Button = React.forwardRef(
  ({ className, variant = 'default', size = 'default', asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';

    const variantClasses = {
      default: 'bg-primary text-primary-foreground hover:bg-primary/90',
      destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
      outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
      secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
      ghost: 'hover:bg-accent hover:text-accent-foreground',
      link: 'text-primary underline-offset-4 hover:underline',
    };

    const sizeClasses = {
      default: 'h-10 px-4 py-2',
      sm: 'h-9 rounded-md px-3',
      lg: 'h-11 rounded-md px-8',
      icon: 'h-10 w-10',
    };

    return (
      <Comp
        className={cn(
          'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
`;

const SHADCN_CARD = `
import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const Card = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
      {...props}
    />
  )
);
Card.displayName = 'Card';

export const CardHeader = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

export const CardTitle = React.forwardRef(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />
  )
);
CardTitle.displayName = 'CardTitle';

export const CardDescription = React.forwardRef(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
  )
);
CardDescription.displayName = 'CardDescription';

export const CardContent = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

export const CardFooter = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';
`;

const SHADCN_BADGE = `
import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function Badge({ className, variant = 'default', ...props }) {
  const variantClasses = {
    default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
    secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
    destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
    outline: 'text-foreground',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}
`;

const SHADCN_SEPARATOR = `
import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export const Separator = React.forwardRef(
  ({ className, orientation = 'horizontal', decorative = true, ...props }, ref) => (
    <div
      ref={ref}
      role={decorative ? 'none' : 'separator'}
      aria-orientation={orientation}
      className={cn(
        'shrink-0 bg-border',
        orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]',
        className
      )}
      {...props}
    />
  )
);
Separator.displayName = 'Separator';
`;

const SHADCN_INTERACTIVE = `
import * as React from 'react';

const passthrough = (tag, extra = {}) => React.forwardRef(({ children, ...props }, ref) => React.createElement(tag, { ...extra, ...props, ref }, children));

export const Carousel = React.forwardRef(({ children, className, ...props }, ref) => <div ref={ref} role="region" aria-roledescription="carousel" data-carousel className={className} {...props}>{children}</div>);
Carousel.displayName = 'Carousel';
export const CarouselContent = React.forwardRef(({ children, className, ...props }, ref) => <div ref={ref} className={className} data-carousel-content {...props}>{children}</div>);
export const CarouselItem = React.forwardRef(({ children, className, ...props }, ref) => <div ref={ref} role="group" aria-roledescription="slide" className={className} data-carousel-item {...props}>{children}</div>);
export const CarouselPrevious = (props) => <button type="button" aria-label="Previous slide" {...props}>Previous</button>;
export const CarouselNext = (props) => <button type="button" aria-label="Next slide" {...props}>Next</button>;

export const Dialog = ({ children, ...props }) => <div data-dialog {...props}>{children}</div>;
Dialog.Root = Dialog;
Dialog.Trigger = ({ children, ...props }) => <button type="button" {...props}>{children}</button>;
Dialog.Content = ({ children, ...props }) => <div role="dialog" aria-modal="true" {...props}>{children}</div>;
Dialog.Title = ({ children, ...props }) => <h2 {...props}>{children}</h2>;
Dialog.Description = ({ children, ...props }) => <p {...props}>{children}</p>;
Dialog.Close = ({ children = 'Close', ...props }) => <button type="button" {...props}>{children}</button>;
export const DialogTrigger = Dialog.Trigger;
export const DialogContent = Dialog.Content;
export const DialogTitle = Dialog.Title;
export const DialogDescription = Dialog.Description;
export const DialogClose = Dialog.Close;

export const Sheet = Dialog;
export const Accordion = ({ children, ...props }) => <div data-accordion {...props}>{children}</div>;
Accordion.Root = Accordion;
Accordion.Item = ({ children, ...props }) => <section {...props}>{children}</section>;
Accordion.Trigger = ({ children, ...props }) => <button type="button" {...props}>{children}</button>;
Accordion.Content = ({ children, ...props }) => <div {...props}>{children}</div>;

export const Tabs = ({ children, ...props }) => <div data-tabs {...props}>{children}</div>;
Tabs.Root = Tabs;
Tabs.List = ({ children, ...props }) => <div role="tablist" {...props}>{children}</div>;
Tabs.Trigger = ({ children, ...props }) => <button type="button" role="tab" {...props}>{children}</button>;
Tabs.Content = ({ children, ...props }) => <div role="tabpanel" {...props}>{children}</div>;
export const TabsList = Tabs.List;
export const TabsTrigger = Tabs.Trigger;
export const TabsContent = Tabs.Content;
export const NavigationMenu = ({ children, ...props }) => <nav {...props}>{children}</nav>;
NavigationMenu.List = ({ children, ...props }) => <ul {...props}>{children}</ul>;
NavigationMenu.Item = ({ children, ...props }) => <li {...props}>{children}</li>;
NavigationMenu.Link = ({ children, ...props }) => <a {...props}>{children}</a>;
export const DropdownMenu = ({ children, ...props }) => <div data-dropdown-menu {...props}>{children}</div>;
DropdownMenu.Root = DropdownMenu;
DropdownMenu.Trigger = ({ children, ...props }) => <button type="button" {...props}>{children}</button>;
DropdownMenu.Content = ({ children, ...props }) => <div role="menu" {...props}>{children}</div>;
DropdownMenu.Item = ({ children, ...props }) => <button type="button" role="menuitem" {...props}>{children}</button>;
export const Tooltip = ({ children, ...props }) => <span data-tooltip {...props}>{children}</span>;
Tooltip.Provider = ({ children }) => <>{children}</>;
Tooltip.Root = Tooltip;
Tooltip.Trigger = ({ children, ...props }) => <span tabIndex="0" {...props}>{children}</span>;
Tooltip.Content = ({ children, ...props }) => <span role="tooltip" {...props}>{children}</span>;
export const Form = ({ children, ...props }) => <form {...props}>{children}</form>;
export const FormField = ({ children, ...props }) => <div data-form-field {...props}>{children}</div>;
export const FormItem = FormField;
export const FormLabel = ({ children, ...props }) => <label {...props}>{children}</label>;
export const FormControl = ({ children }) => <>{children}</>;
export const FormDescription = ({ children, ...props }) => <p {...props}>{children}</p>;
export const FormMessage = ({ children, ...props }) => <p role="alert" {...props}>{children}</p>;
`;

/**
 * Virtual module content for shadcn components.
 */
export function createVirtualModulesPlugin(): Plugin {
  const componentMap: Record<string, string> = {
    button: SHADCN_BUTTON,
    card: SHADCN_CARD,
    badge: SHADCN_BADGE,
    separator: SHADCN_SEPARATOR,
    carousel: SHADCN_INTERACTIVE,
    dialog: SHADCN_INTERACTIVE,
    sheet: SHADCN_INTERACTIVE,
    accordion: SHADCN_INTERACTIVE,
    tabs: SHADCN_INTERACTIVE,
    'navigation-menu': SHADCN_INTERACTIVE,
    'dropdown-menu': SHADCN_INTERACTIVE,
    tooltip: SHADCN_INTERACTIVE,
    form: SHADCN_INTERACTIVE,
  };

  return {
    name: 'virtual-modules',
    setup(build) {
      // Intercept imports to @/components/ui/*
      build.onResolve({ filter: /^@\/components\/ui\// }, (args) => {
        const componentName = args.path.replace('@/components/ui/', '');
        return {
          path: args.path,
          namespace: 'shadcn-virtual',
          pluginData: { componentName },
        };
      });

      // Intercept imports to @/lib/utils
      build.onResolve({ filter: /^@\/lib\/utils$/ }, (args) => {
        return {
          path: args.path,
          namespace: 'shadcn-virtual',
          pluginData: { isUtils: true },
        };
      });

      // Provide the virtual module content
      build.onLoad({ filter: /.*/, namespace: 'shadcn-virtual' }, async (args) => {
        const { componentName, isUtils } = args.pluginData as { componentName?: string; isUtils?: boolean };

        // If it's the utils module
        if (isUtils) {
          return {
            contents: SHADCN_UTILS,
            loader: 'tsx',
            resolveDir: process.cwd(), // Allow resolving node_modules
          };
        }

        // Get component source
        const componentSource = componentMap[componentName || ''];
        if (!componentSource) {
          return {
            errors: [
              {
                text: `Unknown shadcn component: ${componentName}. Available: ${Object.keys(componentMap).join(', ')}`,
              },
            ],
          };
        }

        return {
          contents: componentSource,
          loader: 'tsx',
          resolveDir: process.cwd(), // Allow resolving node_modules
        };
      });
    },
  };
}
