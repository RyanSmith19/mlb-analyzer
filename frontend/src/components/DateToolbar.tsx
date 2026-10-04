type DateToolbarProps = {
  selectedDate: string;
  today: string;
  onDateChange: (date: string) => void;
};

export function DateToolbar({ selectedDate, today, onDateChange }: DateToolbarProps) {
  return (
    <div className="date-toolbar">
      <label className="date-field" htmlFor="game-date">
        <span>Date</span>
        <input
          id="game-date"
          type="date"
          value={selectedDate}
          onChange={(event) => {
            if (event.target.value) onDateChange(event.target.value);
          }}
        />
      </label>
      <button
        className="today-button"
        type="button"
        onClick={() => onDateChange(today)}
        disabled={selectedDate === today}
      >
        Today
      </button>
    </div>
  );
}
