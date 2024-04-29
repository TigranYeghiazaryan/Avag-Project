document.addEventListener("DOMContentLoaded", function () {
    window.requestAnimationFrame(function () {
      const manager = new GameManager(4, KeyboardInputManager, HTMLActuator);
    });
  });
  
  function GameManager(size, InputManager, Actuator) {
    this.size = size;  // Size of the grid
    this.inputManager = new InputManager();
    this.actuator = new Actuator();
    this.startTiles = 2;
  
    this.inputManager.on("move", this.move.bind(this));
    this.inputManager.on("restart", this.restart.bind(this));
  
    this.setup();
  }
  
  GameManager.prototype.restart = function () {
    this.actuator.restart();
    this.setup();
  };
  
  GameManager.prototype.setup = function () {
    this.grid = new Grid(this.size);
    this.score = 0;
    this.over = false;
    this.won = false;
  
    this.addStartTiles();  // Add initial tiles
    this.actuate();        // Update the UI
  };
  
  GameManager.prototype.addStartTiles = function () {
    for (let i = 0; i < this.startTiles; i++) {
      this.addRandomTile();
    }
  };
  
  GameManager.prototype.addRandomTile = function () {
    if (this.grid.cellsAvailable()) {
      const value = Math.random() < 0.9 ? 2 : 4;
      const tile = new Tile(this.grid.randomAvailableCell(), value);
      this.grid.insertTile(tile);
    }
  };
  
  GameManager.prototype.actuate = function () {
    this.actuator.actuate(this.grid, {
      score: this.score,
      over: this.over,
      won: this.won,
    });
  };
  
  GameManager.prototype.prepareTiles = function () {
    this.grid.eachCell((x, y, tile) => {
      if (tile) {
        tile.mergedFrom = null;
        tile.savePosition();
      }
    });
  };
  
  GameManager.prototype.moveTile = function (tile, cell) {
    this.grid.cells[tile.x][tile.y] = null;
    this.grid.cells[cell.x][cell.y] = tile;
    tile.updatePosition(cell);
  };
  
  GameManager.prototype.move = function (direction) {
    if (this.over || this.won) {
      return;
    }
  
    const vector = this.getVector(direction);
    const traversals = this.buildTraversals(vector);
    let moved = false;
  
    this.prepareTiles();  // Prepare tiles for movement
  
    traversals.x.forEach((x) => {
      traversals.y.forEach((y) => {
        const cell = { x: x, y: y };
        const tile = this.grid.cellContent(cell);
  
        if (tile) {
          const positions = this.findFarthestPosition(cell, vector);
          const next = this.grid.cellContent(positions.next);
  
          if (next && next.value === tile.value && !next.mergedFrom) {
            const merged = new Tile(positions.next, tile.value * 2);
            merged.mergedFrom = [tile, next];
  
            this.grid.insertTile(merged);
            this.grid.removeTile(tile);
  
            tile.updatePosition(positions.next);
  
            this.score += merged.value;
  
            if (merged.value === 2048) {
              this.won = true;
            }
          } else {
            this.moveTile(tile, positions.farthest);
          }
  
          if (!this.positionsEqual(cell, tile)) {
            moved = true;
          }
        }
      });
    });
  
    if (moved) {
      this.addRandomTile();
  
      if (!this.movesAvailable()) {
        this.over = true;  // Game over
      }
  
      this.actuate();  // Update the UI
    }
  };
  
  GameManager.prototype.getVector = function (direction) {
    const map = {
      0: { x: 0, y: -1 },  // Up
      1: { x: 1, y: 0 },   // Right
      2: { x: 0, y: 1 },   // Down
      3: { x: -1, y: 0 },  // Left
    };
  
    return map[direction];
  };
  
  GameManager.prototype.buildTraversals = function (vector) {
    const traversals = { x: [], y: [] };
  
    for (let i = 0; i < this.size; i++) {
      traversals.x.push(i);
      traversals.y.push(i);
    }
  
    if (vector.x === 1) {
      traversals.x.reverse();
    }
    if (vector.y === 1) {
      traversals.y.reverse();
    }
  
    return traversals;
  };
  
  GameManager.prototype.findFarthestPosition = function (cell, vector) {
    let previous;
  
    do {
      previous = cell;
      cell = { x: previous.x + vector.x, y: previous.y + vector.y };
    } while (this.grid.withinBounds(cell) && this.grid.cellAvailable(cell));
  
    return {
      farthest: previous,
      next: cell,
    };
  };
  
  GameManager.prototype.movesAvailable = function () {
    return this.grid.cellsAvailable() || this.tileMatchesAvailable();
  };
  
  GameManager.prototype.tileMatchesAvailable = function () {
    for (let x = 0; x < this.size; x++) {
      for (let y = 0; y < this.size; y++) {
        const tile = this.grid.cellContent({ x: x, y: y });
  
        if (tile) {
          for (let dir = 0; dir < 4; dir++) {
            const vector = this.getVector(dir);
            const adjacentCell = { x: x + vector.x, y: y + vector.y };
  
            const adjacentTile = this.grid.cellContent(adjacentCell);
            if (adjacentTile && adjacentTile.value === tile.value) {
              return true;  // Tiles can be merged
            }
          }
        }
      }
    }
  
    return false;
  };
  
  GameManager.prototype.positionsEqual = function (first, second) {
    return first.x === second.x && first.y === second.y;
  };
  
  function Grid(size) {
    this.size = size;
    this.cells = [];
  
    this.build();
  }
  
  Grid.prototype.build = function () {
    for (let x = 0; x < this.size; x++) {
      const row = (this.cells[x] = []);
      for (let y = 0; y < this.size; y++) {
        row.push(null);
      }
    }
  };
  
  Grid.prototype.randomAvailableCell = function () {
    const cells = this.availableCells();
    if (cells.length) {
      return cells[Math.floor(Math.random() * cells.length)];
    }
  };
  
  Grid.prototype.availableCells = function () {
    const cells = [];
  
    this.eachCell((x, y, tile) => {
      if (!tile) {
        cells.push({ x: x, y: y });
      }
    });
  
    return cells;
  };
  
  Grid.prototype.eachCell = function (callback) {
    for (let x = 0; x < this.size; x++) {
      for (let y = 0; y < this.size; y++) {
        callback(x, y, this.cells[x][y]);
      }
    }
  };
  
  Grid.prototype.cellsAvailable = function () {
    return this.availableCells().length > 0;
  };
  
  Grid.prototype.cellAvailable = function (cell) {
    return !this.cellOccupied(cell);
  };
  
  Grid.prototype.cellOccupied = function (cell) {
    return !!this.cellContent(cell);
  };
  
  Grid.prototype.cellContent = function (cell) {
    if (this.withinBounds(cell)) {
      return this.cells[cell.x][cell.y];
    } else {
      return null;
    }
  };
  
  Grid.prototype.withinBounds = function (position) {
    return (
      position.x >= 0 &&
      position.x < this.size &&
      position.y >= 0 &&
      position.y < this.size
    );
  };
  
  function Tile(position, value) {
    this.x = position.x;
    this.y = position.y;
    this.value = value || 2;
  
    this.previousPosition = null;
    this.mergedFrom = null;  // Tracks merged tiles
  }
  
  Tile.prototype.savePosition = function () {
    this.previousPosition = { x: this.x, y: this.y };
  };
  
  Tile.prototype.updatePosition = function (position) {
    this.x = position.x;
    this.y = position.y;
  };
  
  function HTMLActuator() {
    this.tileContainer = document.getElementsByClassName("tile-container")[0];
    this.scoreContainer = document.getElementsByClassName("score-container")[0];
    this.messageContainer = document.getElementsByClassName("game-message")[0];
  
    this.score = 0;
  }
  
  HTMLActuator.prototype.actuate = function (grid, metadata) {
    const self = this;
  
    window.requestAnimationFrame(function () {
      self.clearContainer(self.tileContainer);
  
      grid.cells.forEach((column) => {
        column.forEach((cell) => {
          if (cell) {
            self.addTile(cell);
          }
        });
      });
  
      self.updateScore(metadata.score);
  
      if (metadata.over) {
        self.message(false);  // You lose
      }
      if (metadata.won) {
        self.message(true);  // You win!
      }
    });
  };
  
  HTMLActuator.prototype.restart = function () {
    this.clearMessage();
  };
  
  HTMLActuator.prototype.clearContainer = function (container) {
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
  };
  
  HTMLActuator.prototype.addTile = function (tile) {
    const element = document.createElement("div");
    const position = tile.previousPosition || { x: tile.x, y: tile.y };
    const positionClass = this.positionClass(position);
  
    const classes = ["tile", `tile-${tile.value}`, positionClass];
    this.applyClasses(element, classes);
  
    element.textContent = tile.value;
  
    if (tile.previousPosition) {
      window.requestAnimationFrame(function () {
        classes[2] = self.positionClass({ x: tile.x, y: tile.y });
        self.applyClasses(element, classes);  // Update position
      });
    } else if (tile.mergedFrom) {
      classes.push("tile-merged");
      this.applyClasses(element, classes);
  
      tile.mergedFrom.forEach((merged) => {
        self.addTile(merged);
      });
    } else {
      classes.push("tile-new");
      this.applyClasses(element, classes);
    }
  
    this.tileContainer.appendChild(element);  // Add to tile container
  };
  
  HTMLActuator.prototype.applyClasses = function (element, classes) {
    element.setAttribute("class", classes.join(" "));
  };
  
  HTMLActuator.prototype.positionClass = function (position) {
    position = this.normalizePosition(position);
    return `tile-position-${position.x}-${position.y}`;
  };
  
  HTMLActuator.prototype.normalizePosition = function (position) {
    return { x: position.x + 1, y: position.y + 1 };
  };
  
  HTMLActuator.prototype.updateScore = function (score) {
    this.clearContainer(this.scoreContainer);
  
    const difference = score - this.score;
    this.score = score;
  
    this.scoreContainer.textContent = this.score;
  
    if (difference > 0) {
      const addition = document.createElement("div");
      addition.classList.add("score-addition");
      addition.textContent = `+${difference}`;
  
      this.scoreContainer.appendChild(addition);
    }
  };
  
  HTMLActuator.prototype.message = function (won) {
    const type = won ? "game-won" : "game-over";
    const message = won ? "You win!" : "Game over!";
  
    this.messageContainer.classList.add(type);
    this.messageContainer.getElementsByTagName("p")[0].textContent = message;
  };
  
  HTMLActuator.prototype.clearMessage = function () {
    this.messageContainer.classList.remove("game-won", "game-over");
  };
  
  function KeyboardInputManager() {
    this.events = {};
  
    this.listen();  // Set up event listeners
  }
  
  KeyboardInputManager.prototype.on = function (event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  };
  
  KeyboardInputManager.prototype.emit = function (event, data) {
    const callbacks = this.events[event];
    if (callbacks) {
      callbacks.forEach((callback) => callback(data));
    }
  };
  
  KeyboardInputManager.prototype.listen = function () {
    const self = this;
  
    const keyMap = {
      38: 0, // Up
      39: 1, // Right
      40: 2, // Down
      37: 3, // Left
    };
  
    document.addEventListener("keydown", function (event) {
      const mapped = keyMap[event.which];
      const isModifier = event.altKey || event.ctrlKey || event.metaKey || event.shiftKey;
  
      if (!isModifier) {
        if (mapped !== undefined) {
          event.preventDefault();
          self.emit("move", mapped);  // Trigger move event
        }
  
        if (event.which === 32) {
          self.restart(event);  // Spacebar to restart
        }
      }
    });
  
    const retryButton = document.getElementsByClassName("retry-button")[0];
    retryButton.addEventListener("click", (event) => {
      event.preventDefault();
      self.emit("restart");  // Trigger restart event
    });
  };
  