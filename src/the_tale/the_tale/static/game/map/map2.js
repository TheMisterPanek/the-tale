if (!window.pgf) {
    pgf = {};
}

if (!pgf.game) {
    pgf.game = {};
}

if (!pgf.game.map) {
    pgf.game.map = {};
}

if (!pgf.game.resources) {
    pgf.game.resources = {};
}

if (!pgf.game.resources.events) {
    pgf.game.resources.events = {};
}

if (!pgf.game.map.events) {
    pgf.game.map.events = {};
}

pgf.game.resources.events.SPRITES_LOADED = 'pgf-game-resources-sprites-loaded';
pgf.game.map.events.DATA_UPDATED = 'pgf-game-map-data-updated';
pgf.game.map.events.MAP_RESIZED = 'pgf-game-map-resized';

pgf.game.resources.Image = function(sourceImage, src, x, y, w, h) {

    this.src = src;
    this.x = x;
    this.y = y;
    this.w = w;
    this.h = h;

    var image = document.createElement('canvas');
    image.width = w;
    image.height = h;

    var _tmpContext = image.getContext('2d');
    _tmpContext.drawImage(sourceImage,
                          x, y, w, h,
                          0, 0, w, h);


    this.Draw = function(context, x, y) {
        context.drawImage(image, x, y);
    };
};

pgf.game.resources.ImageManager =  function(spritesSettins, params) {

    var spritesSources = {};

    var loadedSources = 0;
    var totalSources = 0;

    var initializedSprites = 0;
    var totalSprites = 0;

    var sprites = {};

    function InitializeSourceSprites(properties) {
        for( spriteName in spritesSettins) {

            if (typeof(spritesSettins[spriteName])=='string') continue;

            if (spritesSettins[spriteName].src == properties.src) {
                var data = spritesSettins[spriteName];
                sprites[spriteName] = new pgf.game.resources.Image(properties.image, params.staticUrl+properties.src, data.x, data.y, data.w, data.h);
                initializedSprites += 1;
            }
        }

        if (initializedSprites == totalSprites) {
            jQuery(document).trigger(pgf.game.resources.events.SPRITES_LOADED);
        }
    }

    for(spriteName in spritesSettins) {
        var data = spritesSettins[spriteName];

        if (typeof(data)=='string') {
            sprites[spriteName] = data; // store link to real sprite
            continue;
        }

        totalSprites += 1;

        if (spritesSources[data.src] == undefined) {
            spritesSources[data.src] = true;
            totalSources += 1;

            (function() {
                var image = new Image();
                var sourceProperties = { loaded: false,
                                         image: image,
                                         src: data.src,
                                         error: undefined };

                image.onload = function(e) {
                    sourceProperties.loaded = true;
                    loadedSources += 1;
                    InitializeSourceSprites(sourceProperties);
                };
                image.src = params.staticUrl + data.src;
            })();
        }
    }

    this.GetImage = function(name) {
        var sprite = sprites[name];
        if (typeof(sprite)=='string') return this.GetImage(sprite);
        return sprite;
    };

    this.IsReady = function(){ return (initializedSprites == totalSprites); };
};

pgf.game.map.MapManager = function(params) {

    var mapData = {};
    var calculatedData = {};
    var dynamicData = { heroes: {} };
    var instance = this;
    var mapWidth = undefined;
    var mapHeight = undefined;

    function LoadMap() {
        jQuery.ajax({   dataType: 'json',
                        type: 'get',
                        url: params.RegionUrl(),
                        success: function(data, request, status) {
                            mapData = data.data.region;

                            instance.mapWidth = mapData.width;
                            instance.mapHeight = mapData.height;

                            jQuery(document).trigger(pgf.game.map.events.DATA_UPDATED);
                        },
                        error: function() {
                        },
                        complete: function() {
                        }
                    });
    }

    function GetMapDataForRect(x, y, w, h) {
        return { mapData: mapData,
                 dynamicData: dynamicData,
                 calculatedData: calculatedData};
    }

    function GetPlaceData(placeId) {
        if (mapData.places) return mapData.places[placeId];
        return undefined;
    }

    function GetBuildingData(buildingId) {
        return mapData.buildings[buildingId];
    }

    function GetCellData(x, y) {
        var data = { place: undefined,
                     building: undefined};

        for (var placeId in mapData.places) {
            var place = mapData.places[placeId];

            if (place.pos.x == x && place.pos.y == y) {
                data.place = place;
                break;
            }
        }

        for (var buildingId in mapData.buildings) {
            var building = mapData.buildings[buildingId];

            if (building.pos.x == x && building.pos.y == y) {
                data.building = building;
                break;
            }
        }

        return data;
    }

    jQuery(document).bind(pgf.game.events.DATA_REFRESHED, function(e, game_data) {
        if (game_data.account && game_data.account.hero) {
            dynamicData.hero = game_data.account.hero;
        }

        if (mapData && game_data.map_version != mapData.map_version) {
            LoadMap();
        }
    });

    this.mapWidth = 0;
    this.mapHeight = 0;

    this.GetMapDataForRect = GetMapDataForRect;
    this.GetPlaceData = GetPlaceData;
    this.GetCellData = GetCellData;

    LoadMap();
};

pgf.game.map.Map = function(selector, params) {

    var map = jQuery(selector);
    var canvas = jQuery('.pgf-map-canvas', selector);

    var canvasWidth = undefined;
    var canvasHeight = undefined;

    function SyncCanvasSize() {
        canvasWidth = Math.max(jQuery('#pgf-map-container').width()-20, 1);
        canvasHeight = params.canvasHeight;

        canvas.get(0).width = canvasWidth;
        canvas.get(0).height = canvasHeight;

        map.css({width: canvasWidth,
                 height: canvasHeight });
    }
    SyncCanvasSize();

    var spritesManager = params.spritesManager;
    var mapManager = widgets.mapManager;

    var pos = {x: 0, y: 0};

    var TILE_SIZE = params.tileSize;

    var selectedTile = undefined;

    var navigationLayer = new pgf.game.map.NavigationLayer(jQuery('.pgf-navigation-layer'),
                                                           { OnDrag: OnMove,
                                                             OnMouseEnter: OnMouseEnter,
                                                             OnMove: OnMouseMove,
                                                             OnMouseLeave: OnMouseLeave,
                                                             OnClick: OnClick,
                                                             w: canvasWidth,
                                                             h: canvasHeight
                                                           });

    var INITIALIZATION_INFO_LOADED = false;
    var INITIALIZATION_SPRITES_LOADED = false;
    var INITIALIZATION_MAP_LOADED = false;

    var activated = false;

    var showHeroPath = (pgf.base.settings.get("show_hero_path", 'true') == 'true');

    function SwitchHeroPathVisualization() {
        showHeroPath = !showHeroPath;

        pgf.base.settings.set("show_hero_path", showHeroPath);

        var data = mapManager.GetMapDataForRect(pos.x, pos.y, canvasWidth, canvasHeight);
        Draw(data);
    };

    jQuery(window).resize(function(e){
        jQuery(document).trigger(pgf.game.map.events.MAP_RESIZED);
    });

    function IsInitialized() {
        return INITIALIZATION_INFO_LOADED && INITIALIZATION_SPRITES_LOADED && INITIALIZATION_MAP_LOADED;
    }

    function OnClick(offsetX, offsetY) {
        var x =  Math.floor(-(pos.x - offsetX) / TILE_SIZE);
        var y = Math.floor(-(pos.y - offsetY) / TILE_SIZE);

        var cellData = mapManager.GetCellData(x, y);

        pgf.ui.dialog.Create({ fromUrl: '/game/map/cell-info?x='+x+'&y='+y,
                               OnOpened: function(dialog) {
                                   pgf.base.InitializeTabs('game-map-cell-info', 'map',
                                                           [[jQuery('.pgf-cell-description-button', dialog), 'description'],
                                                            [jQuery('.pgf-cell-persons-button', dialog), 'persons'],
                                                            [jQuery('.pgf-cell-place-parameters-button', dialog),'place-parameters'],
                                                            [jQuery('.pgf-cell-place-demographics-button', dialog),'place-demographics'],
                                                            [jQuery('.pgf-cell-place-bills-button', dialog),'place-bills'],
                                                            [jQuery('.pgf-cell-place-modifiers-button', dialog), 'place-modifiers'],
                                                            [jQuery('.pgf-cell-place-character-button', dialog), 'place-character'],
                                                            [jQuery('.pgf-cell-place-chronicle-button', dialog), 'place-chronicle'],
                                                            [jQuery('.pgf-cell-building-button', dialog), 'building'],
                                                            [jQuery('.pgf-cell-map-button', dialog), 'map']]);
                                   jQuery('[rel="tooltip"]', dialog).tooltip(pgf.base.tooltipsArgs);

                                   if (widgets.abilities) {
                                       widgets.abilities.UpdateButtons();
                                       jQuery('.angel-ability', dialog).toggleClass('pgf-hidden', false);
                                   }

                               },
                               OnClosed: function(dialog) {
                                   pgf.base.HideTooltips(dialog);
                               }
                             });
    }

    function OnMouseEnter() {
    }

    function OnMouseLeave() {
        selectedTile = undefined;
        OnMove(0, 0);
    }

    function OnMouseMove(offsetX, offsetY) {
        var needRedraw = false;
        var x =  Math.floor(-(pos.x - offsetX) / TILE_SIZE);
        var y = Math.floor(-(pos.y - offsetY) / TILE_SIZE);
        if (!selectedTile || selectedTile.x != x || selectedTile.y != y) {
            needRedraw = true;
        }
        selectedTile = { x: x, y: y };

        if (needRedraw) OnMove(0, 0);
    }

    function OnMove(dx, dy) {

        if (!IsInitialized()) return;

        pos.x -= dx;
        pos.y -= dy;

        if (pos.x > 0) pos.x = 0;
        if (pos.y > 0) pos.y = 0;
        if (mapManager.mapWidth * TILE_SIZE + pos.x < canvasWidth) pos.x = canvasWidth - mapManager.mapWidth * TILE_SIZE;
        if (mapManager.mapHeight * TILE_SIZE + pos.y < canvasHeight) pos.y = canvasHeight - mapManager.mapHeight * TILE_SIZE;

        var data = mapManager.GetMapDataForRect(pos.x, pos.y, canvasWidth, canvasHeight);
        Draw(data);
    }

    ///////////////////////////////////////////////////
    // cell highlighting
    ///////////////////////////////////////////////////
    var _highlightingBorder = undefined;
    var _highlightingPositions = {};
    function GetHighlightingBorder() {
        if (!_highlightingBorder) {
            image = spritesManager.GetImage('CELL_HIGHLIGHTING');
            _highlightingBorder = jQuery('<div></div>').css({'width': TILE_SIZE+'px',
                                                             'height': TILE_SIZE+'px',
                                                             'background': 'url("'+image.src+'") no-repeat scroll -'+image.x+'px -'+image.y+'px',
                                                             'position': 'relative',
                                                             'display': 'none',
                                                             'z-index': parseInt(canvas.css('z-index')) + 1});
            map.append(_highlightingBorder);
        }
        return _highlightingBorder;
    }

    function UpdateHighlightingPosition(x_, y_) {
        if (x_ != undefined) _highlightingPositions.x = Math.round(x_);
        if (y_ != undefined) _highlightingPositions.y = Math.round(y_);

        var posX = Math.floor(pos.x);
        var posY = Math.floor(pos.y);

        var x = parseInt(posX + _highlightingPositions.x * TILE_SIZE);
        var y = parseInt(posY + _highlightingPositions.y * TILE_SIZE);

        GetHighlightingBorder().css({'left': x+'px', 'top': y+'px'});
    }

    function HighlightCell(x_, y_) {
        UpdateHighlightingPosition(x_, y_);
        GetHighlightingBorder().effect("pulsate", { times:9, mode: "hide"}, 250);
    }
    ///////////////////////////////////////////////////

    function CenterOnHero() {
        var fullData = mapManager.GetMapDataForRect(pos.x, pos.y, canvasWidth, canvasHeight);
        var data = fullData.mapData;

        var hero = fullData.dynamicData.hero;

        if (!hero) return;

        var x = hero.position.x * TILE_SIZE - canvasWidth / 2;
        var y = hero.position.y * TILE_SIZE - canvasHeight / 2;

        OnMove(x + pos.x, y + pos.y);

        HighlightCell(hero.position.x, hero.position.y);

        return;
    }

    function CenterOnPlace(placeId) {
        var fullData = mapManager.GetMapDataForRect(pos.x, pos.y, canvasWidth, canvasHeight);
        var data = fullData.mapData;

        var place = data.places[placeId];

        var x = place.pos.x * TILE_SIZE - canvasWidth / 2;
        var y = place.pos.y * TILE_SIZE - canvasHeight / 2;

        OnMove(x + pos.x, y + pos.y);

        HighlightCell(place.pos.x, place.pos.y);

        return;
    };


    function DrawText(context, text, textWidth, textHeight, x, y) {

        var rectDelta = 2;

        context.textBaseline = 'top';

        context.fillStyle="#000000";
        context.globalAlpha=0.75;
        context.fillRect(x-rectDelta, y-rectDelta, textWidth+rectDelta*2, textHeight+rectDelta*2);
        context.globalAlpha=1;
        context.strokeStyle="#000000";
        context.strokeRect(x-rectDelta, y-rectDelta, textWidth+rectDelta*2, textHeight+rectDelta*2);

        context.fillStyle="#ffffff";

        var chromeY = -2;
        var firefoxY = 1;

        var dY = chromeY;

        if (navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
            dY = firefoxY;
        }

        context.fillText(text, x, y+dY);
    }

    function DrawPathPoint(context, x, y) {
        var pointRadius = 4;
        var borderWidth = 1;

        context.fillStyle = 'black';

        context.beginPath();
        context.arc(x,
                    y,
                    radius=pointRadius,
                    startAngle=0,
                    endAngle=2 * Math.PI);
        context.fill();

        context.fillStyle = 'red';

        context.beginPath();
        context.arc(x,
                    y,
                    radius=pointRadius - borderWidth,
                    startAngle=0,
                    endAngle=2 * Math.PI);
        context.fill();
    }

    function Draw(fullData) {

        if (!IsInitialized()) return;

        var data = fullData.mapData;
        var dynamicData = fullData.dynamicData;
        var calculatedData = fullData.calculatedData;

        var context = canvas.get(0).getContext("2d");

        context.save();

        var posX = Math.floor(pos.x);
        var posY = Math.floor(pos.y);
        var w = data.width;
        var h = data.height;
        var terrain = data.terrain;

        for (var i=0; i<h; ++i) {
            for (var j=0; j<w; ++j) {

                var sprites = data.draw_info[i][j];

                var x = posX + j * TILE_SIZE;
                var y = posY + i * TILE_SIZE;

                for (var sprite_id in sprites) {
                    var sprite_info = sprites[sprite_id];
                    var image = spritesManager.GetImage(sprite_info[0]);

                    var rotate = sprite_info[1] * Math.PI / 180;

                    if (rotate) {
                        context.save();
                        var translated_x = x + TILE_SIZE / 2;
                        var translated_y = y + TILE_SIZE / 2;
                        context.translate(translated_x, translated_y);
                        context.rotate(rotate);
                        image.Draw(context, -TILE_SIZE/2, -TILE_SIZE/2);
                        context.restore();
                    }
                    else {
                        image.Draw(context, x, y);
                    }
                }
            }

        }

        context.font="12px sans-serif";
        for (var place_id in data.places) {
            var place = data.places[place_id];

            var text = '('+place.size+') '+place.name;
            var textWidth = context.measureText(text).width;

            var textX = Math.round(posX + place.pos.x * TILE_SIZE + TILE_SIZE / 2 - textWidth / 2);
            var textY = Math.round(posY + (place.pos.y + 1) * TILE_SIZE)+2;

            DrawText(context,
                     text,
                     textWidth,
                     12,
                     textX,
                     textY);
        }

        var hero = dynamicData.hero;

        if (showHeroPath && hero && hero.path) {
            for (var i = 0; i < hero.path.cells.length; ++i) {
                var cell = hero.path.cells[i];

                DrawPathPoint(context,
                              posX + cell[0] * TILE_SIZE + TILE_SIZE / 2,
                              posY + cell[1] * TILE_SIZE + TILE_SIZE / 2);

                if (i + 1 < hero.path.cells.length) {
                    var nextCell = hero.path.cells[i + 1];

                    DrawPathPoint(context,
                                  posX + (cell[0] + nextCell[0]) / 2 * TILE_SIZE + TILE_SIZE / 2,
                                  posY + (cell[1] + nextCell[1]) / 2 * TILE_SIZE + TILE_SIZE / 2);
                }
            }
        }

        if (hero) {

            var reflectNeeded = (hero.position.dx < 0);

            var image = spritesManager.GetImage(hero.sprite);

            var heroX = parseInt(posX + hero.position.x * TILE_SIZE, 10);
            var heroY = parseInt(posY + hero.position.y * TILE_SIZE, 10) - 12;

            if (reflectNeeded) {
                context.save();
                context.scale(-1, 1);
                heroX *= -1;
                heroX -= TILE_SIZE;
            }

            image.Draw(context, heroX, heroY);

            if (reflectNeeded) {
                context.restore();
            }
        }

        if (selectedTile) {

            var x = posX + selectedTile.x * TILE_SIZE;
            var y = posY + selectedTile.y * TILE_SIZE;

            if (0 <= x && x < w * TILE_SIZE &&
                0 <= y && y < h * TILE_SIZE) {
                var image = spritesManager.GetImage('SELECT_LAND');
                image.Draw(context, x, y);
            }
        }

        context.restore();

        UpdateHighlightingPosition();
    }

    function Activate() {
        activated = true;

        var data = mapManager.GetMapDataForRect(pos.x, pos.y, canvasWidth, canvasHeight).mapData;

        var x = data.width * TILE_SIZE / 2 - canvasWidth / 2;
        var y = data.height * TILE_SIZE / 2- canvasHeight / 2;

        OnMove(x, y);
        CenterOnHero();
    }

    function Refresh(game_data) {
        OnMove(0, 0);
    }

    jQuery(document).bind(pgf.game.events.DATA_REFRESHED,
                          function(e, game_data) {
                              INITIALIZATION_INFO_LOADED = true;

                              if (IsInitialized() && !activated) Activate();

                              widgets.map.Refresh(game_data);
                          });

    jQuery(document).bind(pgf.game.events.GAME_DATA_SHOWED,
                          function(e, game_data) {
                              if (!IsInitialized()) return;

                              SyncCanvasSize();
                              navigationLayer.Resize();
                              CenterOnHero();

                              var data = mapManager.GetMapDataForRect(pos.x, pos.y, canvasWidth, canvasHeight);
                              Draw(data);
                          });

    jQuery(document).bind(pgf.game.map.events.MAP_RESIZED,
                          function(e, game_data) {
                              if (!IsInitialized()) return;

                              SyncCanvasSize();
                              navigationLayer.Resize();
                              // CenterOnHero();

                              var data = mapManager.GetMapDataForRect(pos.x, pos.y, canvasWidth, canvasHeight);
                              Draw(data);
                          });

    jQuery(document).bind(pgf.game.resources.events.SPRITES_LOADED,
                          function() {
                              INITIALIZATION_SPRITES_LOADED = true;
                              if (IsInitialized() && !activated) Activate();
                          });

    jQuery(document).bind(pgf.game.map.events.DATA_UPDATED,
                          function() {
                              INITIALIZATION_MAP_LOADED = true;
                              if (IsInitialized() && !activated) Activate();

                              widgets.map.Refresh();
                          });


    this.Draw = Draw;
    this.CenterOnHero = CenterOnHero;
    this.CenterOnPlace = CenterOnPlace;
    this.SwitchHeroPathVisualization = SwitchHeroPathVisualization;
    this.Refresh = Refresh;
};

pgf.game.map.NavigationLayer = function(selector, params) {

    var container = jQuery(selector);
    container.css({width: params.w,
                   height: params.h});

    var pos = {x: 0, y: 0};

    var OnDrag = params.OnDrag;
    var OnMove = params.OnMove;
    var OnMouseEnter = params.OnMouseEnter;
    var OnMouseLeave = params.OnMouseLeave;
    var OnClick = params.OnClick;

    var layer = this;

    var isDragging = false;

    function OnStartDragging(left, top) {
        pos = {x: left, y: top};
        isDragging = false;
    };

    function OnLayerDrag(left, top) {
        isDragging = true;

        var newPos = {x: left,
                      y: top};

        var delta = {x: pos.x - newPos.x,
                     y: pos.y - newPos.y};

        pos = newPos;

        OnDrag(delta.x, delta.y);
    };

    function OnStopDragging() {
        pos = { x: 0, y: 0};
        isDragging = false;
    };

    container.draggable({start: function(e, ui){OnStartDragging(ui.position.left, ui.position.top);},
                         drag: function(e, ui){OnLayerDrag(ui.position.left, ui.position.top);},
                         stop: function(e, ui){OnStopDragging();},
                         cursor: 'crosshair',
                         helper: 'original',
                         revert: true,
                         revertDuration: 0,
                         scroll: false
                        });

    function _OnMouseMove(pageX, pageY) {
        var offset = container.offset();
        var x = pageX - offset.left;
        var y = pageY - offset.top;
        OnMove(pos.x + x, pos.y + y);
    }

    function _OnClick(pageX, pageY) {
        var offset = container.offset();
        var x = pageX - offset.left;
        var y = pageY - offset.top;
        OnClick(x, y);
    }

    function Resize() {
        params.w = jQuery('#pgf-map-container').width()-20;

        container.css({width: params.w,
                       height: params.h});
    }


    container.mousemove(function(e) {_OnMouseMove(e.pageX, e.pageY);});
    container.mouseenter(function(e){OnMouseEnter();});
    container.mouseleave(function(e){OnMouseLeave();});
    container.click(function(e){_OnClick(e.pageX, e.pageY);});

    container.bind('touchstart', function(e){
                       e.preventDefault(); //prevent block selection on logn touch
                       var touch = e.originalEvent.touches[0] || e.originalEvent.changedTouches[0];
                       OnStartDragging(touch.pageX, touch.pageY);
                   });
    container.bind('touchmove', function(e) {
                       e.preventDefault();
                       var touch = e.originalEvent.touches[0] || e.originalEvent.changedTouches[0];
                       OnLayerDrag(touch.pageX, touch.pageY);
                   });
    container.bind('touchend', function(e){
                       e.preventDefault(); //prevent block selection on logn touch

                       var touch = e.originalEvent.touches[0] || e.originalEvent.changedTouches[0];

                       if (!isDragging) {
                           // emulate mouse click, since we prevent default events handlers
                           _OnClick(touch.pageX, touch.pageY);
                       }

                       OnStopDragging();
                   });

    this.Resize = Resize;
};
