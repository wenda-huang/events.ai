type Props = {
  tags: string[];
  selected: string[];
  onChange: (next: string[]) => void;
};

export function TagPicker({ tags, selected, onChange }: Props) {
  function toggle(tag: string) {
    if (selected.includes(tag)) onChange(selected.filter((t) => t !== tag));
    else onChange([...selected, tag]);
  }

  return (
    <div className="flex flex-wrap gap-2">
      {tags.map((tag) => {
        const on = selected.includes(tag);
        return (
          <button
            key={tag}
            type="button"
            onClick={() => toggle(tag)}
            className={`rounded-full border px-3 py-1 text-xs capitalize tracking-wide ${
              on ? "border-gold bg-gold text-night" : "border-line bg-ink text-mute hover:text-cream"
            }`}
          >
            {tag}
          </button>
        );
      })}
    </div>
  );
}
