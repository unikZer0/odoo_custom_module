from odoo import models, fields

class Book(models.Model):
    _name = 'book.book'
    _description = 'Book'

    name = fields.Char(string='Title',required=True)
    author = fields.Char(string='Author')
    description = fields.Text(string='Description')
    date_release = fields.Date(string='Release Date')
    isbn = fields.Char(string='ISBN')
