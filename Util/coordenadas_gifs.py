# -*- coding: utf-8 -*-
"""
Sistema de Rutas para Delivery - Salto, Uruguay
Calcula rutas óptimas usando Dijkstra/A* sobre el mapa real de calles
"""

import osmnx as ox
import networkx as nx
import random
import heapq
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import io
import os
import pickle
from typing import List, Tuple, Optional

# Variable global para almacenar frames (GIFs)
frames = []

# Variable global para el grafo (se carga una sola vez)
G = None

# Coordenadas del restaurante (centro de Salto)
RESTAURANTE_LAT = -31.3876594
RESTAURANTE_LON = -57.9628518

# Cacheo del grafo
CACHE_DIR = "cache"
GRAFO_CACHE_FILE = os.path.join(CACHE_DIR, "salto_grafo.pkl")


def cargar_o_crear_grafo():
    global G
    
    if G is not None:
        return G
    
    # Intentar cargar desde cache
    if os.path.exists(GRAFO_CACHE_FILE):
        print(f"📦 Cargando grafo desde cache: {GRAFO_CACHE_FILE}")
        try:
            with open(GRAFO_CACHE_FILE, 'rb') as f:
                G = pickle.load(f)
            print(f"✅ Grafo cargado: {len(G.nodes)} nodos, {len(G.edges)} aristas")
            return G
        except Exception as e:
            print(f"⚠️ Error cargando cache: {e}. Descargando nuevamente...")
    
    # Descargar grafo de OpenStreetMap
    print("🌐 Descargando mapa de Salto desde OpenStreetMap...")
    place_name = "Salto, Uruguay"
    G = ox.graph_from_place(place_name, network_type="drive")
    
    # Procesar atributos del grafo (velocidades, pesos, etc.)
    for edge in G.edges:
        maxspeed = 40
        if "maxspeed" in G.edges[edge]:
            maxspeed = G.edges[edge]["maxspeed"]
            if type(maxspeed) == list:
                speeds = [int(speed) for speed in maxspeed]
                maxspeed = min(speeds)
            elif type(maxspeed) == str:
                maxspeed = int(maxspeed)
        G.edges[edge]["maxspeed"] = maxspeed
        G.edges[edge]["weight"] = G.edges[edge]["length"] / maxspeed
    
    # Guardar en cache
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(GRAFO_CACHE_FILE, 'wb') as f:
            pickle.dump(G, f)
        print(f"💾 Grafo guardado en cache: {GRAFO_CACHE_FILE}")
    except Exception as e:
        print(f"⚠️ No se pudo guardar cache: {e}")
    
    print(f"✅ Grafo listo: {len(G.nodes)} nodos, {len(G.edges)} aristas")
    return G

def style_unvisited_edge(edge):
    G.edges[edge]["color"] = "#0000ff" 
    G.edges[edge]["alpha"] = 0.3
    G.edges[edge]["linewidth"] = 0.5

def style_visited_edge(edge):
    G.edges[edge]["color"] = "#0000ff"  
    G.edges[edge]["alpha"] = 0.6
    G.edges[edge]["linewidth"] = 1

def style_active_edge(edge):
    G.edges[edge]["color"] = "#0000ff"  
    G.edges[edge]["alpha"] = 1
    G.edges[edge]["linewidth"] = 1.5

def style_path_edge(edge):
    G.edges[edge]["color"] = "#0000ff"  
    G.edges[edge]["alpha"] = 1
    G.edges[edge]["linewidth"] = 2

def plot_graph_to_image(title="", save_frame=False, frame_num=0):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 12), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')

    ox.plot_graph(
        G,
        ax=ax,
        node_size=[G.nodes[node]["size"] for node in G.nodes],
        edge_color=[G.edges[edge]["color"] for edge in G.edges],
        edge_alpha=[G.edges[edge]["alpha"] for edge in G.edges],
        edge_linewidth=[G.edges[edge]["linewidth"] for edge in G.edges],
        node_color="#0000ff",
        bgcolor="#ffffff",
        show=False,
        close=False
    )
    clean_title = title.encode('ascii', 'ignore').decode('ascii')
    ax.set_title(clean_title, color='blue', fontsize=16, pad=20)

    if save_frame:
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight',
                    facecolor='#ffffff', edgecolor='none', dpi=100)
        buf.seek(0)
        img = Image.open(buf).copy()
        frames.append(img)
        buf.close()

    plt.close()
    return fig


def distance(node1, node2):
    x1, y1 = G.nodes[node1]["x"], G.nodes[node1]["y"]
    x2, y2 = G.nodes[node2]["x"], G.nodes[node2]["y"]
    return ((x2 - x1)**2 + (y2 - y1)**2)**0.5

# ============================================================
# ALGORITMO DE DIJKSTRA
# ============================================================

def dijkstra_gif(orig, dest):
    global frames
    frames = []

    # Inicialización: todos los nodos están sin visitar y a distancia infinita
    for node in G.nodes:
        G.nodes[node]["visited"] = False
        G.nodes[node]["distance"] = float("inf")
        G.nodes[node]["previous"] = None
        G.nodes[node]["size"] = 0
    for edge in G.edges:
        style_unvisited_edge(edge)

    # El nodo origen tiene distancia 0
    G.nodes[orig]["distance"] = 0
    G.nodes[orig]["size"] = 50
    G.nodes[dest]["size"] = 50

    # Cola de prioridad: almacena (distancia_acumulada, nodo)
    pq = [(0, orig)]
    step = 0

    # Guardar frame inicial (para la animación)
    plot_graph_to_image("Dijkstra - Inicio", save_frame=True, frame_num=0)

    # Bucle principal del algoritmo
    while pq:
        # Sacar el nodo con la menor distancia acumulada
        _, node = heapq.heappop(pq)

        # Si llegamos al destino, detenemos el algoritmo
        if node == dest:
            plot_graph_to_image(f"Dijkstra - Destino encontrado! (Iteraciones: {step})",
                                save_frame=True, frame_num=step+1)
            break

        # Si ya fue visitado, lo ignoramos
        if G.nodes[node]["visited"]:
            continue

        # Marcamos el nodo como visitado
        G.nodes[node]["visited"] = True

        # Exploramos sus vecinos
        for edge in G.out_edges(node):
            style_visited_edge((edge[0], edge[1], 0))  # Pintamos la arista explorada
            neighbor = edge[1]
            weight = G.edges[(edge[0], edge[1], 0)]["weight"]

            # Si encontramos un camino más corto hacia el vecino, actualizamos
            if G.nodes[neighbor]["distance"] > G.nodes[node]["distance"] + weight:
                G.nodes[neighbor]["distance"] = G.nodes[node]["distance"] + weight
                G.nodes[neighbor]["previous"] = node
                # Insertamos en la cola con la nueva distancia
                heapq.heappush(pq, (G.nodes[neighbor]["distance"], neighbor))
                # Resaltamos los vecinos activos (en expansión)
                for edge2 in G.out_edges(neighbor):
                    style_active_edge((edge2[0], edge2[1], 0))

        step += 1

        # Guardar frame cada 10 pasos para no generar demasiadas imágenes
        if step % 10 == 0:
            plot_graph_to_image(f"Dijkstra explorando... (Iteracion: {step})",
                                save_frame=True, frame_num=step)

    print(f"Dijkstra completado: {len(frames)} frames capturados")

# ============================================================
# ALGORITMO A*
# ============================================================

def a_star_gif(orig, dest):
    global frames
    frames = []

    # Inicializamos valores de cada nodo
    for node in G.nodes:
        G.nodes[node]["previous"] = None
        G.nodes[node]["size"] = 0
        G.nodes[node]["g_score"] = float("inf")  # costo desde el origen
        G.nodes[node]["f_score"] = float("inf")  # costo estimado total
    for edge in G.edges:
        style_unvisited_edge(edge)

    # Inicializamos el nodo origen
    G.nodes[orig]["size"] = 50
    G.nodes[dest]["size"] = 50
    G.nodes[orig]["g_score"] = 0
    # f = g + h → h se calcula con la distancia euclidiana (heurística)
    G.nodes[orig]["f_score"] = distance(orig, dest)

    # Cola de prioridad: contiene (f_score, nodo)
    pq = [(G.nodes[orig]["f_score"], orig)]
    step = 0

    # Primer frame
    plot_graph_to_image("A* - Inicio", save_frame=True, frame_num=0)

    # Bucle principal del algoritmo A*
    while pq:
        # Tomamos el nodo con menor f_score
        _, node = heapq.heappop(pq)

        # Si llegamos al destino, terminamos
        if node == dest:
            plot_graph_to_image(f"A* - Destino encontrado! (Iteraciones: {step})",
                                save_frame=True, frame_num=step+1)
            break

        # Exploramos los vecinos del nodo actual
        for edge in G.out_edges(node):
            style_visited_edge((edge[0], edge[1], 0))
            neighbor = edge[1]

            # Costo real desde el origen hasta el vecino (g)
            tentative_g_score = G.nodes[node]["g_score"] + distance(node, neighbor)

            # Si encontramos un camino más corto hacia el vecino
            if tentative_g_score < G.nodes[neighbor]["g_score"]:
                # Actualizamos su padre (para reconstruir el camino)
                G.nodes[neighbor]["previous"] = node
                G.nodes[neighbor]["g_score"] = tentative_g_score
                # f = g + h (h = distancia estimada al destino)
                G.nodes[neighbor]["f_score"] = tentative_g_score + distance(neighbor, dest)
                # Insertamos en la cola con prioridad f_score
                heapq.heappush(pq, (G.nodes[neighbor]["f_score"], neighbor))
                # Resaltamos los vecinos activos
                for edge2 in G.out_edges(neighbor):
                    style_active_edge((edge2[0], edge2[1], 0))

        step += 1

        # Guardamos un frame cada 5 pasos (A* suele ser más rápido)
        if step % 5 == 0:
            plot_graph_to_image(f"A* explorando... (Iteracion: {step})",
                                save_frame=True, frame_num=step)

    print(f"A* completado: {len(frames)} frames capturados")

# ============================================================

def reconstruct_path_gif(orig, dest, algorithm_name=""):
    global frames
    if G.nodes[dest]["previous"] is None and dest != orig:
        print("No se encontro un camino valido")
        return False

    for edge in G.edges:
        style_unvisited_edge(edge)

    dist = 0
    speeds = []
    curr = dest
    path_edges = []

    while curr != orig:
        prev = G.nodes[curr]["previous"]
        if prev is None:
            print("Error: Camino incompleto")
            return False
        path_edges.append((prev, curr, 0))
        dist += G.edges[(prev, curr, 0)]["length"]
        speeds.append(G.edges[(prev, curr, 0)]["maxspeed"])
        curr = prev

    for i, edge in enumerate(reversed(path_edges)):
        style_path_edge(edge)
        plot_graph_to_image(f"{algorithm_name} - Construyendo camino... {i+1}/{len(path_edges)}",
                            save_frame=True, frame_num=i)

    dist /= 1000
    final_title = f"{algorithm_name} - CAMINO OPTIMO\n"
    final_title += f"Distancia: {dist:.2f}km | Velocidad: {sum(speeds)/len(speeds):.1f}km/h | Tiempo: {dist/(sum(speeds)/len(speeds)) * 60:.1f}min"
    plot_graph_to_image(final_title, save_frame=True, frame_num=len(path_edges))

    print(f"Distancia: {dist:.2f} km")
    print(f"Velocidad promedio: {sum(speeds)/len(speeds):.1f} km/h")
    print(f"Tiempo total: {dist/(sum(speeds)/len(speeds)) * 60:.1f} minutos")
    print(f"Camino completado: {len(frames)} frames totales")

    return True

def create_gif(algorithm_name, duration=500):
    if not frames:
        print("No hay frames para crear el GIF")
        return None
    filename = f"pathfinding_{algorithm_name.lower()}_salto.gif"
    try:
        frames[0].save(
            filename,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0
        )
        print(f"GIF creado exitosamente: {filename}")
        print(f"{len(frames)} frames | {len(frames)*duration/1000:.1f}s total")
        return filename
    except Exception as e:
        print(f"Error al crear el GIF: {e}")
        return None

def get_coordinates():
    print("SELECCION DE COORDENADAS PARA SALTO, URUGUAY")
    print("=" * 50)
    print("Algunas coordenadas de referencia en Salto:")
    print("   • Centro de Salto: -31.3833, -57.9667")
    print("   • Plaza Artigas: -31.3825, -57.9658")
    print("   • Hospital Regional: -31.3891, -57.9554")
    print("   • Terminal de Omnibus: -31.3878, -57.9640")
    print("   • Costanera Sur: -31.3795, -57.9525")
    print("   • Shopping Salto: -31.3715, -57.9580")

    while True:
        try:
            print("\nPUNTO DE ORIGEN:")
            start_lat = float(input("   Latitud (ej: -31.3833): "))
            start_lon = float(input("   Longitud (ej: -57.9667): "))
            print("\nPUNTO DE DESTINO:")
            end_lat = float(input("   Latitud (ej: -31.3825): "))
            end_lon = float(input("   Longitud (ej: -57.9658): "))
            if not (-31.45 <= start_lat <= -31.30 and -58.10 <= start_lon <= -57.85):
                print("Las coordenadas de origen parecen estar fuera de Salto")
                continue
            if not (-31.45 <= end_lat <= -31.30 and -58.10 <= end_lon <= -57.85):
                print("Las coordenadas de destino parecen estar fuera de Salto")
                continue
            return (start_lat, start_lon), (end_lat, end_lon)
        except ValueError:
            print("Por favor ingresa numeros validos (usa punto decimal, ej: -31.3833)")
        retry = input("\nQuieres intentar de nuevo? (s/n): ").lower()
        if retry != 's':
            print("Usando coordenadas por defecto...")
            return (-31.3833, -57.9667), (-31.3825, -57.9658)

# ============================================================
# FUNCIONES PARA SISTEMA DE DELIVERY
# ============================================================

def encontrar_nodo_cercano(lat: float, lon: float) -> int:
    """
    Encuentra el nodo más cercano en el grafo a las coordenadas dadas.
    
    Args:
        lat: Latitud
        lon: Longitud
    
    Returns:
        ID del nodo más cercano en el grafo
    """
    global G
    cargar_o_crear_grafo()
    
    try:
        nodo = ox.distance.nearest_nodes(G, lon, lat)
        return nodo
    except Exception as e:
        print(f"⚠️ Error encontrando nodo: {e}")
        # Buscar manualmente el nodo más cercano
        min_dist = float('inf')
        closest_node = None
        for node in G.nodes:
            node_lat = G.nodes[node]['y']
            node_lon = G.nodes[node]['x']
            dist = ((lat - node_lat)**2 + (lon - node_lon)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_node = node
        return closest_node


def calcular_ruta_simple(lat_origen: float, lon_origen: float, 
                         lat_destino: float, lon_destino: float) -> Tuple[List, float, float]:
    """
    Calcula la ruta más corta entre dos puntos usando Dijkstra.
    
    Args:
        lat_origen, lon_origen: Coordenadas de origen
        lat_destino, lon_destino: Coordenadas de destino
    
    Returns:
        (lista_nodos_ruta, distancia_km, tiempo_minutos)
    """
    global G
    cargar_o_crear_grafo()
    
    # Encontrar nodos cercanos
    nodo_origen = encontrar_nodo_cercano(lat_origen, lon_origen)
    nodo_destino = encontrar_nodo_cercano(lat_destino, lon_destino)
    
    print(f"🔍 Calculando ruta: {nodo_origen} → {nodo_destino}")
    
    try:
        # Usar el algoritmo de Dijkstra de NetworkX (más simple que nuestra versión)
        ruta = nx.shortest_path(G, nodo_origen, nodo_destino, weight='weight')
        
        # Calcular distancia y tiempo (promedio ponderado por distancia)
        distancia_m = 0
        tiempo_total_min = 0
        
        for i in range(len(ruta) - 1):
            edge_data = G.edges[(ruta[i], ruta[i+1], 0)]
            distancia_seg_m = edge_data['length']
            velocidad_seg_kmh = edge_data.get('maxspeed', 40)
            distancia_m += distancia_seg_m
            
            # Calcular tiempo por segmento
            distancia_seg_km = distancia_seg_m / 1000
            tiempo_seg_min = (distancia_seg_km / velocidad_seg_kmh) * 60
            tiempo_total_min += tiempo_seg_min
        
        distancia_km = distancia_m / 1000
        tiempo_min = tiempo_total_min
        
        print(f"✅ Ruta encontrada: {distancia_km:.2f}km, {tiempo_min:.1f}min")
        
        return ruta, distancia_km, tiempo_min
        
    except nx.NetworkXNoPath:
        print(f"❌ No hay camino entre {nodo_origen} y {nodo_destino}")
        return [], 0, 0
    except Exception as e:
        print(f"❌ Error calculando ruta: {e}")
        return [], 0, 0


def calcular_ruta_tsp(coordenadas: List[Tuple[float, float]]) -> Tuple[List[int], float, float]:
    """
    Resuelve el problema del viajante (TSP) para múltiples puntos de entrega.
    Usa heurística del vecino más cercano (greedy).
    
    Args:
        coordenadas: Lista de tuplas (lat, lon) - PRIMER elemento es el restaurante
    
    Returns:
        (orden_optimo_indices, distancia_total_km, tiempo_total_min)
    """
    global G
    cargar_o_crear_grafo()
    
    if len(coordenadas) < 2:
        return [0], 0, 0
    
    print(f"🚚 Calculando ruta óptima para {len(coordenadas)} puntos...")
    
    # Convertir coordenadas a nodos del grafo
    nodos = []
    for i, (lat, lon) in enumerate(coordenadas):
        nodo = encontrar_nodo_cercano(lat, lon)
        nodos.append(nodo)
        print(f"   Punto {i}: ({lat:.4f}, {lon:.4f}) → Nodo {nodo}")
    
    # Algoritmo del vecino más cercano (greedy TSP)
    visitados = [0]  # Comenzamos desde el restaurante (índice 0)
    distancia_total = 0
    tiempo_total = 0
    
    while len(visitados) < len(nodos):
        nodo_actual_idx = visitados[-1]
        nodo_actual = nodos[nodo_actual_idx]
        
        # Encontrar el nodo más cercano no visitado
        min_distancia = float('inf')
        siguiente_idx = None
        
        for i in range(len(nodos)):
            if i not in visitados:
                try:
                    # Calcular distancia entre nodo_actual y nodo i
                    longitud = nx.shortest_path_length(G, nodo_actual, nodos[i], weight='length')
                    if longitud < min_distancia:
                        min_distancia = longitud
                        siguiente_idx = i
                except:
                    continue
        
        if siguiente_idx is None:
            print(f"No se puede alcanzar punto {len(visitados)}")
            break
        
        # Calcular ruta detallada entre nodo actual y siguiente
        ruta_parcial, dist_km, tiempo_min = calcular_ruta_simple(
            coordenadas[nodo_actual_idx][0], coordenadas[nodo_actual_idx][1],
            coordenadas[siguiente_idx][0], coordenadas[siguiente_idx][1]
        )
        
        visitados.append(siguiente_idx)
        distancia_total += dist_km
        tiempo_total += tiempo_min
        
        print(f"   Paso {len(visitados)-1}: Punto {nodo_actual_idx} → Punto {siguiente_idx} ({dist_km:.2f}km)")
    
    print(f"✅ Ruta TSP completada: {distancia_total:.2f}km, {tiempo_total:.1f}min")
    print(f"   Orden de visita: {' → '.join(map(str, visitados))}")
    
    return visitados, distancia_total, tiempo_total


def generar_imagen_ruta_delivery(coordenadas: List[Tuple[float, float]], 
                                  orden_visita: List[int],
                                  nombre_archivo: str = "ruta_delivery.png",
                                  info_tanda: dict = None,
                                  ubicacion_origen: Optional[Tuple[float, float]] = None) -> str:
    global G
    cargar_o_crear_grafo()
    
    print(f"🎨 Generando imagen de ruta: {nombre_archivo}")
    
    if ubicacion_origen is not None:
        lat_origen, lon_origen = ubicacion_origen
    else:
        lat_origen, lon_origen = coordenadas[0]
    
    if len(coordenadas) < 2:
        print("⚠️ Se necesitan al menos 2 coordenadas (origen y destino)")
        return None
    
    lat_destino, lon_destino = coordenadas[-1] if len(coordenadas) > 1 else coordenadas[0]
    
    for node in G.nodes:
        G.nodes[node]["size"] = 0
    for edge in G.edges:
        G.edges[edge]["color"] = "#0000ff"  # Azul
        G.edges[edge]["alpha"] = 0.3
        G.edges[edge]["linewidth"] = 0.5
    
    nodo_origen = encontrar_nodo_cercano(lat_origen, lon_origen)
    nodo_destino = encontrar_nodo_cercano(lat_destino, lon_destino)
    G.nodes[nodo_origen]["size"] = 100
    G.nodes[nodo_destino]["size"] = 80
    
    distancia_total = 0
    tiempo_total_min = 0
    velocidades = []
    
    try:
        ruta_segmento = nx.shortest_path(G, nodo_origen, nodo_destino, weight='weight')
        
        for j in range(len(ruta_segmento) - 1):
            edge = (ruta_segmento[j], ruta_segmento[j+1], 0)
            G.edges[edge]["color"] = "#0000ff"
            G.edges[edge]["alpha"] = 1
            G.edges[edge]["linewidth"] = 2
            
            distancia_seg_m = G.edges[edge]["length"]
            velocidad_seg_kmh = G.edges[edge].get("maxspeed", 40)
            distancia_total += distancia_seg_m
            velocidades.append(velocidad_seg_kmh)
            
            distancia_seg_km = distancia_seg_m / 1000
            tiempo_seg_min = (distancia_seg_km / velocidad_seg_kmh) * 60
            tiempo_total_min += tiempo_seg_min
    except Exception as e:
        print(f"No se pudo dibujar ruta: {e}")
        distancia_total = 0
        tiempo_total_min = 0
        velocidades = []
    
    distancia_km = distancia_total / 1000
    velocidad_promedio = sum(velocidades) / len(velocidades) if velocidades else 40
    tiempo_min = tiempo_total_min
    
    if info_tanda:
        titulo = f"Tanda #{info_tanda.get('id_tanda', '?')} - Próximo pedido\n"
        titulo += f"Distancia: {distancia_km:.2f}km | Tiempo estimado: {int(tiempo_min)}min | Vel. prom: {int(velocidad_promedio)}km/h"
    else:
        titulo = f"Ruta de Delivery\n"
        titulo += f"{distancia_km:.2f}km | {int(tiempo_min)} min"
    
    fig, ax = plt.subplots(figsize=(12, 12), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')
    
    ox.plot_graph(
        G,
        ax=ax,
        node_size=[G.nodes[node]["size"] for node in G.nodes],
        edge_color=[G.edges[edge]["color"] for edge in G.edges],
        edge_alpha=[G.edges[edge]["alpha"] for edge in G.edges],
        edge_linewidth=[G.edges[edge]["linewidth"] for edge in G.edges],
        node_color="#0000ff",  
        bgcolor="#ffffff",  
        show=False,
        close=False
    )
    
    ax.set_title(titulo, color='#0000ff', fontsize=16, pad=20)
    
    os.makedirs("temp", exist_ok=True)
    ruta_completa = os.path.join("temp", nombre_archivo)
    plt.savefig(ruta_completa, format='png', bbox_inches='tight',
                facecolor='#ffffff', edgecolor='none', dpi=100)
    plt.close()
    
    print(f" Imagen guardada: {ruta_completa}")
    print(f" {distancia_km:.2f}km |  {tiempo_min} min")
    
    return ruta_completa


def calcular_y_generar_ruta_tanda(pedidos_tanda: List[dict], id_tanda: int, ubicacion_origen: Optional[Tuple[float, float]] = None) -> Tuple[str, dict]:
    print(f"{'='*60}")
    print(f"CALCULANDO RUTA PARA TANDA #{id_tanda}")
    print(f"{'='*60}")

    if not pedidos_tanda or len(pedidos_tanda) == 0:
        raise ValueError("ERROR: No hay pedidos en la tanda")

    pedido = pedidos_tanda[0]
    lat_pedido = float(pedido.get('latitud', pedido.get('lat', 0)))
    lon_pedido = float(pedido.get('longitud', pedido.get('lon', 0)))

    if lat_pedido == 0 or lon_pedido == 0:
        raise ValueError(
            f"ERROR: Pedido {pedido.get('idpedido')} tiene coordenadas inválidas "
            f"({lat_pedido}, {lon_pedido}). No se puede calcular la ruta."
        )

    if ubicacion_origen is not None:
        lat_origen, lon_origen = ubicacion_origen
        origen_texto = f"Ubicación actual ({lat_origen:.4f}, {lon_origen:.4f})"
    else:
        if RESTAURANTE_LAT == 0 or RESTAURANTE_LON == 0:
            raise ValueError("ERROR: Las coordenadas del restaurante no pueden ser 0,0.")
        lat_origen, lon_origen = RESTAURANTE_LAT, RESTAURANTE_LON
        origen_texto = f"Restaurante ({RESTAURANTE_LAT:.4f}, {RESTAURANTE_LON:.4f})"

    print(f"   Origen: {origen_texto}")
    print(f"   Destino: Pedido #{pedido.get('idpedido')} ({lat_pedido:.4f}, {lon_pedido:.4f}) - {pedido.get('direccion', 'Sin dirección')}")

    ruta_nodos, distancia_km, tiempo_min = calcular_ruta_simple(
        lat_origen, lon_origen,
        lat_pedido, lon_pedido
    )

    if not ruta_nodos:
        raise ValueError("ERROR: No se pudo calcular la ruta")

    coordenadas = [(lat_origen, lon_origen), (lat_pedido, lon_pedido)]
    orden_visita = [0, 1]

    info_tanda = {
        'id_tanda': id_tanda,
        'num_pedidos': 1
    }

    nombre_archivo = f"tanda_{id_tanda}_ruta.png"
    ruta_imagen = generar_imagen_ruta_delivery(
        coordenadas, orden_visita, nombre_archivo, info_tanda, ubicacion_origen
    )

    info = {
        'distancia_km': round(distancia_km, 2),
        'tiempo_min': round(tiempo_min, 0),
        'orden_visita': orden_visita,
        'num_entregas': 1,
        'ruta_imagen': ruta_imagen
    }

    print(f"RUTA CALCULADA EXITOSAMENTE")
    print(f"   Distancia: {distancia_km:.2f} km")
    print(f"   Tiempo estimado: {int(tiempo_min)} minutos")
    print(f"   Imagen: {ruta_imagen}")
    print(f"{'='*60}")

    return ruta_imagen, info