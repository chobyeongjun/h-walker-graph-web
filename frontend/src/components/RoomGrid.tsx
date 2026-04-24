import { DoorOpen, Plus, LayoutGrid, Database } from 'lucide-react';
import { usePage } from '../store/page';

export default function RoomGrid() {
  const rooms = usePage((s) => s.rooms);
  const datasets = usePage((s) => s.datasets);
  const cells = usePage((s) => s.cells);
  const setActiveRoom = usePage((s) => s.setActiveRoom);
  const createRoom = usePage((s) => s.createRoom);
  const showToast = usePage((s) => s.showToast);

  function handleNewRoom() {
    const name = window.prompt('New room name:', `Room ${rooms.length + 1}`);
    if (!name || !name.trim()) return;
    const id = createRoom(name.trim(), []);
    setActiveRoom(id);
    showToast(`Room "${name}" created`);
  }

  function handleEnterAll() {
    setActiveRoom(null);
    // activeRoomId === null falls back to 거실 (all cells) — but we want a
    // dedicated flag, so the grid doesn't re-show. Canvas handles this
    // by checking showAllCells via sessionStorage.
    sessionStorage.setItem('hw_showAll', '1');
    window.dispatchEvent(new Event('hw_showAll_change'));
  }

  return (
    <div className="room-grid">
      <div className="room-grid-head">
        <span className="room-grid-ey">WORKSPACE</span>
        <h1>Rooms</h1>
        <p className="room-grid-sub">
          각 방은 비교할 데이터들을 묶어둔 작업 공간이에요.
          업로드 시 파일명 prefix로 자동 배정되고, 수동으로 만들 수도 있어요.
        </p>
      </div>

      <div className="room-grid-cards">
        {rooms.map((r) => {
          const dsCount = r.datasetIds.length;
          const cellCount = r.cellIds.length;
          return (
            <button
              key={r.id}
              className="room-card"
              onClick={() => setActiveRoom(r.id)}
              title={`Enter room "${r.name}"`}
            >
              <div className="room-card-icon"><DoorOpen size={22} /></div>
              <div className="room-card-name">{r.name}</div>
              <div className="room-card-meta">
                <span><Database size={11} /> {dsCount} datasets</span>
                <span><LayoutGrid size={11} /> {cellCount} cells</span>
              </div>
            </button>
          );
        })}

        <button
          className="room-card room-card-new"
          onClick={handleNewRoom}
          title="Create an empty room"
        >
          <div className="room-card-icon"><Plus size={22} /></div>
          <div className="room-card-name">New Room</div>
          <div className="room-card-meta">
            <span>빈 방 만들기</span>
          </div>
        </button>

        {cells.length > 0 && (
          <button
            className="room-card room-card-all"
            onClick={handleEnterAll}
            title="Show every cell across all rooms"
          >
            <div className="room-card-icon"><LayoutGrid size={22} /></div>
            <div className="room-card-name">거실 (All)</div>
            <div className="room-card-meta">
              <span>{cells.length} cells · {datasets.length} datasets</span>
            </div>
          </button>
        )}
      </div>
    </div>
  );
}
