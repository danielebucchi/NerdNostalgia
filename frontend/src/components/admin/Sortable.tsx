"use client";

import { ReactNode } from "react";
import {
  DndContext,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  horizontalListSortingStrategy,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

type SortStrategy = "rect" | "vertical" | "horizontal";

interface ItemRenderProps {
  isDragging: boolean;
  listeners: ReturnType<typeof useSortable>["listeners"];
  attributes: ReturnType<typeof useSortable>["attributes"];
}

interface SortableProps<T> {
  items: T[];
  getKey: (item: T) => string;
  onReorder: (next: T[]) => void;
  renderItem: (item: T, index: number, props: ItemRenderProps) => ReactNode;
  className?: string;
  strategy?: SortStrategy;
}

const STRATEGY = {
  rect: rectSortingStrategy,
  vertical: verticalListSortingStrategy,
  horizontal: horizontalListSortingStrategy,
} as const;

export function Sortable<T>({
  items,
  getKey,
  onReorder,
  renderItem,
  className,
  strategy = "rect",
}: SortableProps<T>) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 220, tolerance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((i) => getKey(i) === active.id);
    const newIndex = items.findIndex((i) => getKey(i) === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    onReorder(arrayMove(items, oldIndex, newIndex));
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={items.map(getKey)} strategy={STRATEGY[strategy]}>
        <div className={className}>
          {items.map((item, index) => (
            <SortableItem key={getKey(item)} id={getKey(item)}>
              {(props) => renderItem(item, index, props)}
            </SortableItem>
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

/** Back-compat alias (le pagine articoli importavano SortableImageGrid). */
export const SortableImageGrid = Sortable;

interface SortableItemProps {
  id: string;
  children: (props: ItemRenderProps) => ReactNode;
}

function SortableItem({ id, children }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    touchAction: "none",
    zIndex: isDragging ? 10 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      {children({ listeners, attributes, isDragging })}
    </div>
  );
}
