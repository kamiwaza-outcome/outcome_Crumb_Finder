'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface CollapsibleProps {
  /**
   * The header/trigger content
   */
  trigger: React.ReactNode;
  
  /**
   * The collapsible content
   */
  children: React.ReactNode;
  
  /**
   * Whether the collapsible is open by default
   */
  defaultOpen?: boolean;
  
  /**
   * Controlled open state
   */
  open?: boolean;
  
  /**
   * Callback when open state changes
   */
  onOpenChange?: (open: boolean) => void;
  
  /**
   * Whether to show a chevron icon
   */
  showChevron?: boolean;
  
  /**
   * Position of the chevron
   */
  chevronPosition?: 'left' | 'right';
  
  /**
   * Additional CSS classes for the container
   */
  className?: string;
  
  /**
   * Additional CSS classes for the trigger
   */
  triggerClassName?: string;
  
  /**
   * Additional CSS classes for the content
   */
  contentClassName?: string;
}

/**
 * Collapsible component with smooth animations.
 * 
 * Features:
 * - Smooth height animations
 * - Controlled and uncontrolled modes
 * - Customizable trigger and content
 * - Keyboard navigation support
 * 
 * @example
 * ```tsx
 * <Collapsible
 *   trigger={<h3>Click to expand</h3>}
 *   defaultOpen={false}
 *   showChevron
 * >
 *   <p>This content is collapsible!</p>
 * </Collapsible>
 * ```
 */
export function Collapsible({
  trigger,
  children,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
  showChevron = true,
  chevronPosition = 'right',
  className = '',
  triggerClassName = '',
  contentClassName = ''
}: CollapsibleProps) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | undefined>(undefined);
  
  // Determine if component is controlled
  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : internalOpen;

  // Handle open state changes
  const handleToggle = () => {
    const newOpen = !isOpen;
    
    if (!isControlled) {
      setInternalOpen(newOpen);
    }
    
    onOpenChange?.(newOpen);
  };

  // Update height when open state changes
  useEffect(() => {
    if (contentRef.current) {
      if (isOpen) {
        setHeight(contentRef.current.scrollHeight);
      } else {
        setHeight(0);
      }
    }
  }, [isOpen]);

  // Update height on content changes
  useEffect(() => {
    if (isOpen && contentRef.current) {
      const resizeObserver = new ResizeObserver(() => {
        setHeight(contentRef.current?.scrollHeight);
      });

      resizeObserver.observe(contentRef.current);

      return () => {
        resizeObserver.disconnect();
      };
    }
  }, [isOpen, children]);

  return (
    <div className={`collapsible ${className}`}>
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isOpen}
        className={`
          w-full flex items-center justify-between
          text-left cursor-pointer
          transition-colors duration-200
          ${triggerClassName}
        `}
      >
        {showChevron && chevronPosition === 'left' && (
          <span className="mr-2 transition-transform duration-200">
            {isOpen ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>
        )}
        
        <span className="flex-1">{trigger}</span>
        
        {showChevron && chevronPosition === 'right' && (
          <span className="ml-2 transition-transform duration-200">
            {isOpen ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>
        )}
      </button>
      
      <div
        ref={contentRef}
        style={{
          height: height,
          overflow: 'hidden',
          transition: 'height 0.3s ease'
        }}
        className={contentClassName}
      >
        <div className="pt-2">
          {children}
        </div>
      </div>
    </div>
  );
}

interface AccordionItem {
  id: string;
  trigger: React.ReactNode;
  content: React.ReactNode;
}

interface AccordionProps {
  /**
   * Array of accordion items
   */
  items: AccordionItem[];
  
  /**
   * Whether only one item can be open at a time
   */
  single?: boolean;
  
  /**
   * Default open items (array of IDs)
   */
  defaultOpen?: string[];
  
  /**
   * Whether to show chevron icons
   */
  showChevron?: boolean;
  
  /**
   * Additional CSS classes
   */
  className?: string;
  
  /**
   * Additional CSS classes for items
   */
  itemClassName?: string;
}

/**
 * Accordion component for multiple collapsible sections.
 * 
 * @example
 * ```tsx
 * <Accordion
 *   single
 *   items={[
 *     {
 *       id: '1',
 *       trigger: 'Section 1',
 *       content: 'Content for section 1'
 *     },
 *     {
 *       id: '2',
 *       trigger: 'Section 2',
 *       content: 'Content for section 2'
 *     }
 *   ]}
 * />
 * ```
 */
export function Accordion({
  items,
  single = false,
  defaultOpen = [],
  showChevron = true,
  className = '',
  itemClassName = ''
}: AccordionProps) {
  const [openItems, setOpenItems] = useState<string[]>(defaultOpen);

  const handleOpenChange = (itemId: string, open: boolean) => {
    if (single) {
      setOpenItems(open ? [itemId] : []);
    } else {
      setOpenItems((prev) =>
        open
          ? [...prev, itemId]
          : prev.filter((id) => id !== itemId)
      );
    }
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {items.map((item) => (
        <div
          key={item.id}
          className={`border border-gray-200 dark:border-gray-700 rounded-lg ${itemClassName}`}
        >
          <Collapsible
            trigger={item.trigger}
            open={openItems.includes(item.id)}
            onOpenChange={(open) => handleOpenChange(item.id, open)}
            showChevron={showChevron}
            triggerClassName="p-4 hover:bg-gray-50 dark:hover:bg-gray-800"
            contentClassName="px-4 pb-4"
          >
            {item.content}
          </Collapsible>
        </div>
      ))}
    </div>
  );
}