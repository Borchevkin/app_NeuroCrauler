#!/usr/bin/env python3

import math
import pygame
from pygame.locals import *
from pygame.color import *
import pymunk
import pymunk.pygame_util
from pymunk.vec2d import Vec2d
from pybrain.structure import FeedForwardNetwork
from pybrain.structure import LinearLayer, SigmoidLayer, FullConnection
import serial


class NeuroCrawler(object):
    """docstring for NeuroCrawler"""

    def __init__(self, space, start_line, ground_level,
                 hull_size=(200.0, 50.0), hull_mass=1500, arm_mass=200,
                 segment_lengths=[100, 75]):
        self.space = space
        self.initial_shift = Vec2d(start_line, ground_level)
        self.hull_size = Vec2d(hull_size)
        self.hull_mass = hull_mass
        self._add_hull()
        self.initial_position = self.hull.body.position
        self.arm_segments = []
        self.arm_servos = []
        segment_mass_scale = arm_mass / sum(segment_lengths)
        segment_joint_point = self.initial_shift + self.hull_size
        for segment_length in segment_lengths:
            segment_mass = segment_mass_scale * segment_length
            self._add_arm_segment(segment_length, segment_mass,
                                  segment_joint_point)
            self._add_arm_servo(segment_joint_point)
            segment_joint_point.y += segment_length
        else:
            self._add_sensor(segment_length / 2)
        self.brain = Brain(4, 8, 2)

    def _add_hull(self):
        HULL_FRICTION = 0.25
        hull_moment = pymunk.moment_for_box(self.hull_mass, self.hull_size)
        hull_body = pymunk.Body(self.hull_mass, hull_moment)
        hull_body.position = self.initial_shift + self.hull_size / 2
        self.hull = pymunk.Poly.create_box(hull_body, size=self.hull_size)
        self.hull.friction = HULL_FRICTION
        self.space.add(self.hull, self.hull.body)

    def _add_arm_segment(self, segment_length, segment_mass,
                         segment_joint_point):
        SEGMENT_WIDTH = 20.0
        segment_size = Vec2d(SEGMENT_WIDTH, segment_length)
        segment_moment = pymunk.moment_for_box(segment_mass, segment_size)
        segment_body = pymunk.Body(segment_mass, segment_moment)
        segment_body.position = segment_joint_point + \
            Vec2d(0, segment_length / 2)
        segment = pymunk.Poly.create_box(segment_body, size=segment_size)
        self.space.add(segment, segment.body)
        self.arm_segments.append(segment)

    def _add_arm_servo(self, joint_point):
        hull_servo_angle_min = -math.pi / 2
        hull_servo_angle_max = math.pi
        arm_servo_angle_min = -math.pi
        arm_servo_angle_max = math.pi
        if len(self.arm_segments) < 2:
            self.arm_servos.append(ServoMotor(
                self.space, self.hull, self.arm_segments[-1], joint_point,
                hull_servo_angle_min, hull_servo_angle_max))
        else:
            self.arm_servos.append(ServoMotor(
                self.space, self.arm_segments[-2], self.arm_segments[-1],
                joint_point, arm_servo_angle_min, arm_servo_angle_max))

    def _add_sensor(self, sensor_position):
        SENSOR_RADIUS = 15.0
        SENSOR_FRICTION = 1.0
        self.sensor = SensorShape(
            self.arm_segments[-1].body, SENSOR_RADIUS,
            Vec2d(0, sensor_position))
        self.sensor.friction = SENSOR_FRICTION
        self.space.add(self.sensor)

    def _get_state(self):
        info = [servo.position for servo in self.arm_servos]
        info.append(position_from_angle(
            self.hull.body.angle % math.pi, -math.pi, math.pi))
        info.append(self.sensor.is_triggered)
        return info

    def set_servos_positions(self, new_positions):
        for serv, new_position in zip(self.arm_servos, new_positions):
            serv.move_to_position(new_position)

    def move(self):
        print(self.brain.make_decision(self._get_state()))
        self.set_servos_positions(
            self.brain.make_decision(self._get_state()))

    def odometer(self):
        return self.hull.body.position - self.initial_position


class ServoMotor(object):
    """set of constraints which emulate servo motor"""
    INITIAL_ANGLE = 0.0
    STIFFNESS = 3 * 10**8
    DUMPING = 5 * 10**6
    MAX_FORCE = 10**10

    def __init__(self, space, object_a, object_b, joint_point,
                 angle_min, angle_max):
        self.angle_min = angle_min
        self.angle_max = angle_max
        self.shaft = pymunk.constraint.PivotJoint(
            object_a.body,
            object_b.body,
            joint_point)
        self.shaft.collide_bodies = False
        self.shaft.max_force = self.MAX_FORCE
        self.shaft.error_bias = math.pow(0.5, 60)
        self.motor = pymunk.constraint.DampedRotarySpring(
            object_a.body,
            object_b.body,
            self.INITIAL_ANGLE,
            self.STIFFNESS,
            self.DUMPING)
        self.motor.max_force = self.MAX_FORCE
        space.add(self.shaft, self.motor)
        self.position = position_from_angle(
            self.INITIAL_ANGLE, self.angle_min, self.angle_max)

    def move_to_position(self, new_position):
        self.position = new_position
        self.motor.rest_angle = angle_from_position(
            new_position, self.angle_min, self.angle_max)


class SensorShape(pymunk.Circle):
    def __init__(self, body, radius, offset):
        pymunk.Circle.__init__(self, body, radius, offset=offset)
        self.is_triggered = False


class Brain(object):
    """feed forward neural net for servos control"""

    def __init__(self, in_layer_size, hidden_layer_size, out_layer_size):
        self.network = FeedForwardNetwork()
        in_layer = LinearLayer(in_layer_size)
        hidden_layer = SigmoidLayer(hidden_layer_size)
        out_layer = SigmoidLayer(out_layer_size)
        self.network.addInputModule(in_layer)
        self.network.addModule(hidden_layer)
        self.network.addOutputModule(out_layer)
        in_to_hidden = FullConnection(in_layer, hidden_layer)
        hidden_to_out = FullConnection(hidden_layer, out_layer)
        self.network.addConnection(in_to_hidden)
        self.network.addConnection(hidden_to_out)
        self.network.sortModules()

    def make_decision(self, currnet_state):
        return self.network.activate(currnet_state).tolist()


def add_terranian(space, height=50, length=600, type='flat'):
    SURFACE_WIDTH = 2.0
    if type == 'flat':
        surface = pymunk.Segment(space.static_body,
                                 (0.0, height), (length, height),
                                 SURFACE_WIDTH)
    elif type == 'slopes':
        raise RuntimeError('Not implemented')
    elif type == 'steps':
        raise RuntimeError('Not implemented')
    else:
        raise ValueError('Unknown terrainian type: {0!s}'.format(type))
    surface.friction = 0.5
    surface.group = 0
    space.add(surface)


def position_from_angle(angle, angle_min, angle_max):
    return (angle - angle_min) / (angle_max - angle_min)


def angle_from_position(position, angle_min, angle_max):
    return position * angle_max + (1 - position) * angle_min


def activate_sensors(arbiter, space, data):
    for shape in arbiter.shapes:
        try:
            shape.is_triggered = True
        except AttributeError:
            pass


def deactivate_sensors(arbiter, space, data):
    for shape in arbiter.shapes:
        try:
            shape.is_triggered = False
        except AttributeError:
            pass


def main():
    pygame.init()
    screen = pygame.display.set_mode((600, 600))
    clock = pygame.time.Clock()
    space = pymunk.Space()
    handler = space.add_default_collision_handler()
    handler.post_solve = activate_sensors
    handler.separate = deactivate_sensors
    space.gravity = Vec2d(0.0, -1000.0)
    draw_options = pymunk.pygame_util.DrawOptions(screen)
    add_terranian(space)
    test_crauler = NeuroCrawler(space, 100, 50)
    running = True
    srv1 = 0.5
    srv2 = 0.5
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    srv1 = srv1 - 0.05 if srv1 > 0 else 0
                    test_crauler.set_servos_positions([srv1, srv2])
                if event.key == K_LEFT:
                    srv2 = srv2 - 0.05 if srv2 > 0 else 0
                    test_crauler.set_servos_positions([srv1, srv2])
                if event.key == K_DOWN:
                    srv1 = srv1 + 0.05 if srv1 < 1 else 1
                    test_crauler.set_servos_positions([srv1, srv2])
                if event.key == K_RIGHT:
                    srv2 = srv2 + 0.05 if srv2 < 1 else 1
                    test_crauler.set_servos_positions([srv1, srv2])
                elif event.key == K_SPACE:
                    test_crauler.move()
                elif event.key == K_ESCAPE:
                    running = False
        screen.fill(THECOLORS["white"])
        space.debug_draw(draw_options)
        dt = 1.0 / 60
        space.step(dt)
        pygame.display.flip()
        clock.tick(50)
        text = 'x: {0:4.1f}, y: {1:4.1f}'.format(
            test_crauler.odometer().x, test_crauler.odometer().y)
        pygame.display.set_caption(text)

if __name__ == '__main__':
    main()

