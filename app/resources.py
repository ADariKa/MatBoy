from flask_restful import reqparse, abort, Resource, request
from flask_restful.inputs import boolean
from flask import jsonify
from data import User, Team, Tournament, League, Game, create_session
from datetime import date
from config import config
import logging


def get_date_from_string(strdate: str) -> date:
    return date.fromisoformat('-'.join(reversed(strdate.split("."))))


def get_user(session, user_id=None, email=None, do_abort=True) -> User:
    """Get User from database, abort(404) if do_abort==True and user not found

       If user.id and user.email specified in the same time
       user was looking by user.id"""
    if user_id:
        user = session.query(User).get(user_id)
        if do_abort and not user:
            abort(404, message=f"User #{user_id} not found")
    elif email:
        user = session.query(User).filter(User.email == email.lower()).first()
        if do_abort and not user:
            abort(404, message=f"User with email {email} not found")
    else:
        return None
    return user


def get_team(session, team_id, do_abort=True) -> Team:
    """Get Team from database, abort(404) if do_abort==True and team not found"""
    team = session.query(Team).get(team_id)
    if do_abort and not team:
        abort(404, message=f"Team #{team_id} not found")
    return team


def get_tour(session, tour_id, do_abort=True) -> Tournament:
    """Get Tournament from database, abort(404) if do_abort==True and tournament not found"""
    tour = session.query(Tournament).get(tour_id)
    if do_abort and not tour:
        abort(404, message=f"Tournament #{tour_id} not found")
    return tour


def get_league(session, league_id, do_abort=True) -> League:
    """Get League from database, abort(404) if do_abort==True and league not found"""
    league = session.query(League).get(league_id)
    if do_abort and not league:
        abort(404, message=f"League #{league_id} not found")
    return league


def abort_if_email_exist(session, email):
    if session.query(User).filter(User.email == email).first():
        abort(409, message=f"User wiht email {repr(email)} alredy exist")


class UserResource(Resource):
    def get(self, user_id: int):
        session = create_session()
        return jsonify({"user": get_user(session, user_id).to_dict()})

    def delete(self, user_id):
        """Only admin can delete"""
        # TODO: UserResource delete
        pass


class UsersResource(Resource):
    reg_pars = reqparse.RequestParser()
    reg_pars.add_argument('surname', required=True, type=str)
    reg_pars.add_argument('name', required=True, type=str)
    reg_pars.add_argument('patronymic', required=False, type=str)
    reg_pars.add_argument('city', required=False, type=str)
    reg_pars.add_argument('birthday', required=True, type=get_date_from_string)
    reg_pars.add_argument('email', required=True, type=str)
    reg_pars.add_argument('password', required=True, type=str)

    def post(self):
        args = UsersResource.reg_pars.parse_args()
        session = create_session()
        abort_if_email_exist(session, args['email'])
        user = User().fill(email=args['email'],
                           name=args['name'],
                           surname=args['surname'],
                           patronymic=args['patronymic'],
                           city=args['city'],
                           birthday=args['birthday'],
                           )
        user.set_password(args['password'])
        session.add(user)
        session.commit()
        return jsonify({"success": "ok"})

    def get(self):
        session = create_session()
        users = session.query(User).all()
        json_resp = {"users": [user.to_dict(only=(
            "id",
            "name",
            "surname",
            "email",
        )) for user in users]}
        return jsonify(json_resp)


class TeamResource(Resource):
    put_pars = reqparse.RequestParser()
    put_pars.add_argument('name', type=str)
    put_pars.add_argument('motto', type=str)
    put_pars.add_argument('status', type=int)
    put_pars.add_argument('trainer.id', type=int)
    put_pars.add_argument('trainer.email', type=str)
    put_pars.add_argument('trainer', type=dict)
    put_pars.add_argument('league.id', type=int)  # 0 == None
    put_pars.add_argument('send_info', type=boolean, default=False)

    def get(self, team_id: int):
        session = create_session()
        team = get_team(session, team_id)
        return jsonify({'team': team.to_dict()})

    def put(self, team_id):
        """If trainer.id and trainer.email specified in the same time
           trainer was looking by trainer.id"""
        args = self.put_pars.parse_args()
        logging.info(f"Team put request with args {args}")
        session = create_session()
        team = get_team(session, team_id)
        if not(args['trainer.id'] is None and args['trainer.email'] is None):
            team.trainer = get_user(session,
                                    user_id=args['trainer']['id'],
                                    email=args['trainer']['email'],
                                    )
        if args['league.id'] is not None:
            if args['league.id'] == 0:
                team.league = None
            else:
                team.league = get_league(session, args['league.id'])
        if args['name'] is not None:
            team.name = args['name']
        if args['motto'] is not None:
            team.motto = args['motto']
        if args['status'] is not None:
            team.status = args['status']
        session.merge(team)
        session.commit()
        
        response = {'success': 'ok'}
        if args['send_info']:
            response['team'] = team.to_dict()
        return response

    def delete(self, team_id):
        session = create_session()
        team = get_team(session, team_id)
        team.status = 0
        session.merge(team)
        session.commit()
        return jsonify({'success': 'ok'})


class LeagueResource(Resource):
    put_pars = reqparse.RequestParser()
    put_pars.add_argument('title', type=str)
    put_pars.add_argument('description', type=str)
    put_pars.add_argument('chief.id', type=int)
    put_pars.add_argument('chief.email', type=str)
    put_pars.add_argument('tournament.id', type=int)  # 0 == None
    put_pars.add_argument('send_info', type=boolean, default=False)

    def get(self, league_id: int):
        session = create_session()
        league = get_league(session, league_id)
        return jsonify({'league': league.to_dict()})

    def put(self, league_id):
        """Handle request to change league."""
        args = self.put_pars.parse_args()
        logging.info(f"League put request with args {args}")
        
        session = create_session()
        league = get_league(session, league_id)
        if not(args['chief.id'] is None and args['chief.email'] is None):
            league.chief = get_user(session,
                                    user_id=args['chief.id'],
                                    email=args['chief.email'],
                                    )
        if args['tournament.id'] is not None:
            if args['tournament.id'] == 0:
                league.tournament = None
            else:
                league.tournament = get_tour(session, args['tournament.id'])
        if args['title'] is not None:
            league.title = args['title']
        if args['description'] is not None:
            league.description = args['description']
        session.merge(league)
        session.commit()
        
        response = {"success": "ok"}
        if args['send_info']:
            response["league"] = league.to_dict()
        return jsonify(response)

    def delete(self, league_id):
        session = create_session()
        league = get_league(session, league_id)
        session.delete(league)
        session.commit()
        return jsonify({'success': 'ok'})


class LeaguesResource(Resource):
    post_pars = LeagueResource.put_pars.copy()
    post_pars.replace_argument('title', type=str, required=True)
    post_pars.add_argument('tournament.id', type=int, required=True)

    def post(self):
        """Handle request to create league."""
        args = self.post_pars.parse_args()
        logging.info(f"League post request with args {args}")
        
        session = create_session()
        league = League()
        if args['chief.id'] is None and args['chief.email'] is None:
            abort(400, message={"chief": "Missing required parameter in the JSON body."})
        else:
            league.chief = get_user(session,
                                    user_id=args['chief.id'],
                                    email=args['chief.email'],)
        league.tournament = get_tour(session, args['tournament.id'])
        league.title = args['title']
        if args['description'] is not None:
            league.description = args['description']
        session.add(league)
        session.commit()
        
        response = {"success": "ok"}
        if args['send_info']:
            response["league"] = league.to_dict()
        return jsonify(response)